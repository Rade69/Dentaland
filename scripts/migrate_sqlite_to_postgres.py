"""Jednokratan CLI za kopiranje podataka SQLite -> PostgreSQL (DENT-IMPROVE-012).

KRITIČNO — NIKAD ne pokretati ovaj skript nad
``C:\\Users\\38765\\Desktop\\Dentaland\\dentaland.db`` (glavni repo, lokalni
dev fajl). Provjereno 27.8.2026 (read-only, ``mode=ro``) da taj fajl sadrži
STVARAN pacijentski zapis (ime/telefon/email koji se poklapaju sa vlasnikom
projekta), ne sintetske test podatke — vidi OUT_OF_SCOPE_FINDING u
``agent_reports/2026-08-27-DENT-IMPROVE-012-plan.md`` i finalnom izvještaju
za ovaj task. Ovaj skript prima izvor generički (``--source-sqlite``) zbog
višekratne upotrebe u budućnosti (npr. stvarna produkcijska migracija tek
nakon Radovanove eksplicitne odluke o toj bazi), ali je u OVOM tasku
testiran isključivo nad svježe generisanom sintetskom SQLite bazom.

FK-safe redoslijed insertovanja: ``doctors`` -> ``services`` ->
``working_hours``/``time_off``/``appointments`` (oba zavise od ``doctors``;
``appointments`` dodatno od ``services``). Kopiranje ide na Core (Table)
nivou, ne kroz ORM identity map — svaka tabela se čita SELECT-om iz izvora
i upisuje INSERT-om u odredište preko istog ``dentaland.models.Base``
metadata objekta, pa isti ``TZDateTime`` tip (src/dentaland/models.py)
garantuje timezone-aware (UTC) vrijednosti i pri čitanju i pri upisu, bez
obzira na SQL dijalekt.

Upotreba:
    python scripts/migrate_sqlite_to_postgres.py \\
        --source-sqlite path/to/synthetic.db \\
        --target-url postgresql://user:pass@localhost:5433/dentaland_test \\
        [--truncate-target] [--dry-run]

``--truncate-target`` briše postojeće redove (u FK-bezbjednom obrnutom
redoslijedu) iz odredišnih tabela prije kopiranja — koristno za ponovljivo
testiranje nad istom test bazom. ``--dry-run`` samo ispisuje broj redova u
izvoru po tabeli, ne dodiruje odredište.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from sqlalchemy import Table, create_engine, insert, select
from sqlalchemy.engine import Engine

from dentaland.models import (
    Appointment,
    Base,
    Doctor,
    Service,
    TimeOff,
    WorkingHours,
)

# Roditelji prije djece — jedini bezbjedan redoslijed za INSERT uz FK.
_MODELS_IN_ORDER: list[type] = [Doctor, Service, WorkingHours, TimeOff, Appointment]


@dataclass
class TableIntegrityReport:
    name: str
    source_count: int
    target_count: int
    fk_violations: list[str]
    status_counts_source: dict[str, int] | None = None
    status_counts_target: dict[str, int] | None = None

    @property
    def ok(self) -> bool:
        return self.source_count == self.target_count and not self.fk_violations


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source-sqlite",
        required=True,
        help="Putanja do izvorne SQLite baze (npr. sintetska test baza). "
        "Skript je otvara READ-ONLY (mode=ro).",
    )
    parser.add_argument(
        "--target-url",
        required=True,
        help="SQLAlchemy URL odredišne PostgreSQL baze (npr. iz DATABASE_URL_TEST).",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Prije kopiranja obriši postojeće redove iz odredišnih tabela "
        "(obrnut FK-bezbjedan redoslijed). Koristi se za ponovljivo testiranje.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Samo ispiši broj redova po tabeli u izvoru, ne diraj odredište.",
    )
    return parser.parse_args(argv)


def _source_engine(path: str) -> Engine:
    # mode=ro -- eksplicitno read-only, skript nikad ne piše u izvor.
    return create_engine(f"sqlite:///file:{path}?mode=ro&uri=true")


def _truncate_target(target_engine: Engine) -> None:
    with target_engine.begin() as conn:
        for model in reversed(_MODELS_IN_ORDER):
            table: Table = model.__table__
            conn.execute(table.delete())


def _copy_table(source_engine: Engine, target_engine: Engine, model: type) -> tuple[int, int]:
    table: Table = model.__table__
    with source_engine.connect() as source_conn:
        rows = [dict(r._mapping) for r in source_conn.execute(select(table))]

    if rows:
        with target_engine.begin() as target_conn:
            target_conn.execute(insert(table), rows)

    with target_engine.connect() as target_conn:
        target_count = len(target_conn.execute(select(table)).fetchall())

    return len(rows), target_count


def _reset_sequences(target_engine: Engine) -> None:
    """Postgres serial/identity sekvence se ne pomjeraju automatski kad se
    ID eksplicitno upisuje preko INSERT-a (ne kroz nextval()) -- bez ovoga
    bi sljedeći "prirodan" INSERT (npr. iz aplikacije nakon migracije)
    mogao pokušati iskoristiti već zauzet ID."""
    from sqlalchemy import text

    with target_engine.begin() as conn:
        for model in _MODELS_IN_ORDER:
            table_name = model.__tablename__
            conn.execute(
                text(
                    "SELECT setval("
                    "pg_get_serial_sequence(:table_name, 'id'), "
                    "COALESCE((SELECT MAX(id) FROM " + table_name + "), 1), "
                    "(SELECT MAX(id) FROM " + table_name + ") IS NOT NULL"
                    ")"
                ),
                {"table_name": table_name},
            )


def _fk_spot_check(target_engine: Engine) -> list[str]:
    """Provjeri da svaka non-null FK referenca u odredištu zaista pokazuje
    na postojeći red -- ne samo da je INSERT prošao bez greške (Postgres bi
    inače sam odbio FK kršenje, ali ovo je eksplicitna, čitljiva potvrda za
    izvještaj, ne oslanjanje na "nije pukao")."""
    from sqlalchemy import text

    violations: list[str] = []
    checks = [
        ("working_hours", "doctor_id", "doctors"),
        ("time_off", "doctor_id", "doctors"),
        ("appointments", "doctor_id", "doctors"),
        ("appointments", "service_id", "services"),
    ]
    with target_engine.connect() as conn:
        for child_table, fk_col, parent_table in checks:
            result = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM {child_table} c "
                    f"WHERE c.{fk_col} IS NOT NULL AND NOT EXISTS "
                    f"(SELECT 1 FROM {parent_table} p WHERE p.id = c.{fk_col})"
                )
            ).scalar_one()
            if result:
                violations.append(
                    f"{child_table}.{fk_col} -> {parent_table}.id: {result} orphan red(ova)"
                )
    return violations


def _status_counts(engine: Engine) -> dict[str, int]:
    from sqlalchemy import func

    table = Appointment.__table__
    with engine.connect() as conn:
        rows = conn.execute(
            select(table.c.status, func.count()).group_by(table.c.status)
        ).all()
    return {str(status): count for status, count in rows}


def run_migration(
    source_path: str, target_url: str, truncate_target: bool, dry_run: bool
) -> list[TableIntegrityReport]:
    source_engine = _source_engine(source_path)

    if dry_run:
        reports = []
        with source_engine.connect() as conn:
            for model in _MODELS_IN_ORDER:
                count = len(conn.execute(select(model.__table__)).fetchall())
                reports.append(
                    TableIntegrityReport(
                        name=model.__tablename__,
                        source_count=count,
                        target_count=-1,
                        fk_violations=[],
                    )
                )
        source_engine.dispose()
        return reports

    target_engine = create_engine(target_url)
    # Osiguraj da šema postoji (no-op ako je alembic upgrade head već
    # primijenjen -- create_all je idempotentan). NAPOMENA (Pi review N1):
    # ovo NE garantuje da je šema stvarno građena kroz Alembic migracije --
    # ako `alembic upgrade head` nikad nije pokrenut, `create_all` će tiho
    # napraviti šemu direktno iz `models.py`, mimoilazeći migracionu
    # istoriju. Ovaj skript pretpostavlja da je Alembic već autoritet nad
    # šemom (kako je i testirano), ne koristiti ga kao zamjenu za
    # `alembic upgrade head` na novoj bazi.
    Base.metadata.create_all(target_engine)

    if truncate_target:
        _truncate_target(target_engine)

    reports = []
    for model in _MODELS_IN_ORDER:
        src_count, tgt_count = _copy_table(source_engine, target_engine, model)
        reports.append(
            TableIntegrityReport(
                name=model.__tablename__,
                source_count=src_count,
                target_count=tgt_count,
                fk_violations=[],
            )
        )

    _reset_sequences(target_engine)

    fk_violations = _fk_spot_check(target_engine)
    for report in reports:
        if report.name == "appointments" or any(v.startswith(report.name) for v in fk_violations):
            report.fk_violations = [v for v in fk_violations if v.startswith(report.name)]

    source_status = _status_counts(source_engine)
    target_status = _status_counts(target_engine)
    for report in reports:
        if report.name == "appointments":
            report.status_counts_source = source_status
            report.status_counts_target = target_status

    source_engine.dispose()
    target_engine.dispose()
    return reports


def _print_report(reports: list[TableIntegrityReport], dry_run: bool) -> None:
    print("\n=== Integrity report ===")
    print(f"{'table':<18}{'source_count':<14}{'target_count':<14}{'status'}")
    all_ok = True
    for r in reports:
        status = "DRY-RUN" if dry_run else ("OK" if r.ok else "MISMATCH")
        if not dry_run and not r.ok:
            all_ok = False
        print(f"{r.name:<18}{r.source_count:<14}{r.target_count:<14}{status}")
        if r.fk_violations:
            for v in r.fk_violations:
                print(f"    FK VIOLATION: {v}")
        if r.status_counts_source is not None:
            print(f"    status counts (source): {r.status_counts_source}")
            print(f"    status counts (target): {r.status_counts_target}")
            if r.status_counts_source != r.status_counts_target:
                all_ok = False
                print("    STATUS COUNT MISMATCH")
    if not dry_run:
        print(f"\nOverall: {'OK' if all_ok else 'FAILED'}")
        if not all_ok:
            sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    reports = run_migration(
        source_path=args.source_sqlite,
        target_url=args.target_url,
        truncate_target=args.truncate_target,
        dry_run=args.dry_run,
    )
    _print_report(reports, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
