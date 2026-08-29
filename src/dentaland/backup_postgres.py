"""Backup PostgreSQL baze — ``pg_dump``/``pg_restore`` + enkripcija + rotacija.

Paralelan modul uz ``dentaland.backup`` (SQLite, Faza 0) — pokriva CLAUDE.md /
``docs/dentaland-razvojni-plan-v3.1.md`` zahtjev: "Dnevni ``pg_dump`` backup
(Faza 1+) + **testiran** restore, ne samo napravljen." (DENT-IMPROVE-016).

Razlike u odnosu na SQLite backup (namjerne, ne nedovršenost):

- Koristi stvarne ``pg_dump``/``pg_restore`` izvršne fajlove (subprocess) —
  ne reimplementira dump logiku u Pythonu; format ``custom`` (``-Fc``,
  kompresovan, pogodan za ``pg_restore``).
- Enkripcija: isti Fernet pristup kao SQLite backup, ali **poseban ključ**
  (``backup_postgres.key``, ne dijeli se sa SQLite ključem) — dva odvojena
  rizična domena, curenje jednog ne kompromituje drugi.
- Rotacija je pojednostavljena (samo "zadrži zadnjih N", bez
  dnevno/mjesečnog razdvajanja kao kod SQLite) — proporcionalno obimu
  jedne ordinacije (CLAUDE.md), ne treba dvoslojna šema za ovaj obim.
- ``restore_test`` NIKAD ne piše preko aktivne baze — kreira privremenu
  bazu (``CREATE DATABASE``), radi restore u nju, verifikuje, pa je briše
  (``DROP DATABASE``).
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2  # type: ignore[import-untyped]
from cryptography.fernet import Fernet, InvalidToken
from psycopg2 import sql  # type: ignore[import-untyped]
from sqlalchemy.engine import URL, make_url

from dentaland import paths
from dentaland.backup import BackupError, ensure_key, load_key

BACKUP_PREFIX = "dentaland-pg-"
BACKUP_SUFFIX = ".dump.enc"
LAST_BACKUP_FILENAME = "last_backup.txt"
KEY_FILENAME = "backup_postgres.key"
RESTORE_TEST_DB_SUFFIX = "_restore_check"
STALE_AFTER = timedelta(hours=25)

# Tabele koje moraju postojati i biti čitljive u restore-ovanoj bazi da bi se
# restore smatrao integritetski ispravnim (DENT-IMPROVE-014 audit_events
# uključen — cijela trenutna Dentaland šema, ne samo appointments). Vidi
# Codex review F1 (2026-08-29) — provjera SAMO appointments je prihvatala
# adversarnu bazu sa proizvoljnom praznom tabelom istog imena.
CORE_TABLES = (
    "doctors",
    "services",
    "working_hours",
    "time_off",
    "appointments",
    "users",
    "sessions",
    "audit_events",
)

ENV_DATABASE_URL = "DATABASE_URL"
ENV_PG_BIN_DIR = "DENTALAND_PG_BIN_DIR"


class RestoreVerificationError(BackupError):
    """Restore je uspio kao proces, ali podaci nisu prošli integritetsku provjeru."""


@dataclass
class PostgresBackupConfig:
    """Putevi i pravila rotacije za PostgreSQL backup.

    ``key_path`` je namjerno odvojen od SQLite backup ključa (vidi modul
    docstring). ``local_dir``/``cloud_dir`` idu u ``postgres/`` podfolder
    ispod postojećih backup putanja da se dump fajlovi ne miješaju sa
    SQLite ``.db.enc`` fajlovima.
    """

    database_url: str
    local_dir: Path
    cloud_dir: Path
    key_path: Path
    daily_keep: int = 30


@dataclass(frozen=True)
class RestoreTestResult:
    """Rezultat ``restore_test`` — dokaz šta je stvarno provjereno.

    ``table_counts`` je manifest broja redova po tabeli u PRIVREMENOJ bazi
    u trenutku provjere (prije nego što je obrisana) — konkretan dokaz da
    su podaci stvarno restore-ovani, ne samo da je proces vratio exit 0.
    """

    backup_path: Path
    table_counts: dict[str, int]
    throwaway_db_name: str


def build_config(env: Mapping[str, str] | None = None) -> PostgresBackupConfig:
    """Sastavi ``PostgresBackupConfig`` iz env varijabli."""
    environ: Mapping[str, str] = os.environ if env is None else env
    database_url = environ.get(ENV_DATABASE_URL)
    if not database_url:
        raise BackupError(f"{ENV_DATABASE_URL} nije postavljen.")
    return PostgresBackupConfig(
        database_url=database_url,
        local_dir=paths.backup_dir(env) / "postgres",
        cloud_dir=paths.backup_cloud_dir(env) / "postgres",
        key_path=paths.config_dir(env) / KEY_FILENAME,
    )


def _resolve_binary(name: str, env: Mapping[str, str] | None) -> str:
    """Nađi putanju do ``pg_dump``/``pg_restore`` izvršnog fajla.

    Redoslijed: ``DENTALAND_PG_BIN_DIR`` override → PATH → standardna
    Windows instalacija (dev convenience — produkcija na Linux VPS-u
    normalno ima ove alate na PATH-u kroz ``postgresql-client``).
    """
    environ: Mapping[str, str] = os.environ if env is None else env
    exe = f"{name}.exe" if sys.platform == "win32" else name

    override_dir = environ.get(ENV_PG_BIN_DIR)
    if override_dir:
        candidate = Path(override_dir) / exe
        if candidate.exists():
            return str(candidate)
        raise BackupError(f"{name} nije nađen u {override_dir} ({ENV_PG_BIN_DIR}).")

    found = shutil.which(name)
    if found:
        return found

    for candidate in sorted(Path("C:/Program Files/PostgreSQL").glob(f"*/bin/{exe}"), reverse=True):
        return str(candidate)

    raise BackupError(
        f"{name} nije pronađen (ni na PATH-u ni u standardnoj instalaciji). "
        f"Postavi {ENV_PG_BIN_DIR} na folder sa pg_dump/pg_restore izvršnim fajlovima."
    )


def _encrypt(plain_path: Path, enc_path: Path, key: bytes) -> None:
    enc_path.write_bytes(Fernet(key).encrypt(plain_path.read_bytes()))


def _decrypt(enc_path: Path, plain_path: Path, key: bytes) -> None:
    try:
        data = Fernet(key).decrypt(enc_path.read_bytes())
    except InvalidToken as exc:
        raise BackupError(f"Neispravan ključ ili oštećen backup: {enc_path}") from exc
    plain_path.write_bytes(data)


def _url_without_password(database_url: str) -> str:
    """URL bez lozinke — bezbjedan za argv (proces command-line je vidljiv
    kroz procesnu inspekciju/task manager). Lozinka ide kroz ``PGPASSWORD``
    env varijablu umjesto toga (vidi ``_pg_subprocess_env``).

    ``URL.set(password=None)`` je NAMJERNO izbjegnut — ``None`` tu znači
    "ne mijenjaj", ne "obriši" (SQLAlchemy sentinel), pa bi tiho ostavio
    lozinku u stringu. ``URL.create()`` bez ``password`` argumenta daje
    čist ``user@host`` (bez dvotačke) — jednoznačno za libpq (prazna
    lozinka "user:@host" bi značila doslovno praznu lozinku, ne "koristi
    PGPASSWORD").
    """
    url = make_url(database_url)
    return URL.create(
        drivername=url.drivername,
        username=url.username,
        host=url.host,
        port=url.port,
        database=url.database,
        query=url.query,
    ).render_as_string(hide_password=False)


def _pg_subprocess_env(database_url: str) -> dict[str, str]:
    """Environment za pg_dump/pg_restore subprocess.

    UVIJEK puni ``os.environ`` (ne bilo koji ``env`` override mapping) —
    subprocess-u trebaju PATH/SYSTEMROOT i sl. da uopšte radi (npr. DNS
    resolution na Windowsu puca bez njih); override mape koje pozivaoci
    koriste za DENTALAND_* konfiguraciju NISU zamjena za pravi OS
    environment. Dodaje ``PGPASSWORD`` da lozinka ne mora u argv.
    """
    base = dict(os.environ)
    password = make_url(database_url).password
    if password:
        base["PGPASSWORD"] = password
    return base


def _database_name(database_url: str) -> str:
    # Ne ispisivati database_url u poruci - moze sadrzati lozinku.
    name = make_url(database_url).database
    if not name:
        raise BackupError("DATABASE_URL nema ime baze (putanja iza posljednjeg '/').")
    return name


def _backup_filename(database_url: str, now: datetime) -> str:
    db_name = _database_name(database_url)
    return f"{BACKUP_PREFIX}{db_name}-{now:%Y-%m-%d}{BACKUP_SUFFIX}"


def _list_backups(cloud_dir: Path) -> list[Path]:
    return sorted(cloud_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"), reverse=True)


def _latest_backup(cloud_dir: Path) -> Path | None:
    files = _list_backups(cloud_dir)
    return files[0] if files else None


def rotate_backups(config: PostgresBackupConfig) -> list[Path]:
    """Zadrži zadnjih ``daily_keep`` dumpova, obriši ostalo; vrati obrisane."""
    files = _list_backups(config.cloud_dir)
    to_delete = files[config.daily_keep :]
    for path in to_delete:
        path.unlink(missing_ok=True)
    return to_delete


def _write_last_backup(cloud_dir: Path, when: datetime) -> None:
    (cloud_dir / LAST_BACKUP_FILENAME).write_text(when.isoformat() + "\n")


def _run_pg_dump(pg_dump_bin: str, database_url: str, dest_path: Path) -> None:
    url = _url_without_password(database_url)
    result = subprocess.run(
        [pg_dump_bin, "--format=custom", f"--file={dest_path}", url],
        capture_output=True,
        text=True,
        env=_pg_subprocess_env(database_url),
    )
    if result.returncode != 0:
        raise BackupError(f"pg_dump nije uspio (exit {result.returncode}): {result.stderr.strip()}")


def _run_pg_restore(pg_restore_bin: str, target_url: str, dump_path: Path) -> None:
    result = subprocess.run(
        [
            pg_restore_bin,
            "--clean",
            "--if-exists",
            f"--dbname={_url_without_password(target_url)}",
            str(dump_path),
        ],
        capture_output=True,
        text=True,
        env=_pg_subprocess_env(target_url),
    )
    if result.returncode != 0:
        raise BackupError(
            f"pg_restore nije uspio (exit {result.returncode}): {result.stderr.strip()}"
        )


def _throwaway_db_name(database_url: str) -> str:
    """Jedinstveno ime po pozivu — NIKAD deterministički samo iz izvorne baze.

    Codex review F2 (2026-08-29): determinističko ime + bezuslovan DROP
    IF EXISTS prije kreiranja bi mogao obrisati postojeću, nepovezanu bazu
    sa istim imenom. Nasumičan sufiks čini svaki poziv bezbjedno jedinstven
    — DROP IF EXISTS u cleanup-u je siguran jer je ovo ime garantovano
    kreirano (ili nikad nije postojalo) u OVOM pozivu.
    """
    token = secrets.token_hex(8)
    return f"{_database_name(database_url)}{RESTORE_TEST_DB_SUFFIX}_{token}"


def _throwaway_url(database_url: str, throwaway_name: str) -> str:
    return make_url(database_url).set(database=throwaway_name).render_as_string(hide_password=False)


def _drop_database_sql(name: str) -> sql.Composed:
    return sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name))


def _create_throwaway_database(admin_url: str, throwaway_name: str) -> None:
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(_drop_database_sql(throwaway_name))
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(throwaway_name)))
    finally:
        conn.close()


def _drop_throwaway_database(admin_url: str, throwaway_name: str) -> None:
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(_drop_database_sql(throwaway_name))
    finally:
        conn.close()


def _verify_postgres_db(database_url: str) -> dict[str, int]:
    """Potvrdi da restore-ovana baza ima KOMPLETNU očekivanu šemu i vrati
    manifest broja redova po tabeli (dokaz integriteta, ne samo "readable").

    Codex review F1 (2026-08-29): ranija verzija je provjeravala samo
    ``appointments`` bez pamćenja rezultata — adversarna baza sa
    proizvoljnom praznom tabelom istog imena je prolazila. Provjera svih
    ``CORE_TABLES`` hvata i taj slučaj (nepotpuna/lažna šema puca na prvoj
    tabeli koje nema) i daje pozivaocu konkretne brojeve za dalju provjeru.
    """
    try:
        conn = psycopg2.connect(database_url)
    except psycopg2.OperationalError as exc:
        raise RestoreVerificationError(f"Restore-test baza nije dostupna: {exc}") from exc
    try:
        counts: dict[str, int] = {}
        with conn.cursor() as cur:
            for table in CORE_TABLES:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                row = cur.fetchone()
                counts[table] = row[0]
        return counts
    except psycopg2.Error as exc:
        raise RestoreVerificationError(
            f"Restore-test baza nije čitljiva/kompletna: {exc}"
        ) from exc
    finally:
        conn.close()


def create_backup(
    config: PostgresBackupConfig,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> Path:
    """Napravi enkriptovan ``pg_dump`` i vrati putanju do njega."""
    now = now or datetime.now().astimezone()
    config.local_dir.mkdir(parents=True, exist_ok=True)
    config.cloud_dir.mkdir(parents=True, exist_ok=True)

    key = ensure_key(config.key_path)
    pg_dump_bin = _resolve_binary("pg_dump", env)
    local_tmp = config.local_dir / "backup-tmp.dump"
    try:
        _run_pg_dump(pg_dump_bin, config.database_url, local_tmp)
        enc_path = config.cloud_dir / _backup_filename(config.database_url, now)
        _encrypt(local_tmp, enc_path, key)
    finally:
        local_tmp.unlink(missing_ok=True)

    rotate_backups(config)
    _write_last_backup(config.cloud_dir, now)
    return enc_path


def restore_test(
    config: PostgresBackupConfig, env: Mapping[str, str] | None = None
) -> RestoreTestResult:
    """Dekriptuj najnoviji backup, restore u PRIVREMENU bazu, verifikuj, obriši je.

    Nikad ne dira ``config.database_url`` bazu samu — koristi se samo kao
    admin konekcija za ``CREATE``/``DROP DATABASE`` privremene test baze.
    Ime privremene baze je jedinstveno po pozivu (``_throwaway_db_name``),
    pa je cleanup u ``finally`` ispod bezbjedan bez obzira GDJE tačno
    unutar bloka nešto pukne — uključujući odmah nakon ``CREATE DATABASE``
    (Codex review F3, 2026-08-29: ranija verzija je imala kreiranje IZVAN
    try/finally koji radi cleanup, pa je izuzetak tu ostavljao bazu iza
    sebe).
    """
    enc_path = _latest_backup(config.cloud_dir)
    if enc_path is None:
        raise BackupError(f"Nema backupa za testiranje u: {config.cloud_dir}")
    key = load_key(config.key_path)

    pg_restore_bin = _resolve_binary("pg_restore", env)
    dump_tmp = config.local_dir / "restore-test.dump"
    throwaway_name = _throwaway_db_name(config.database_url)
    throwaway_url = _throwaway_url(config.database_url, throwaway_name)
    try:
        _decrypt(enc_path, dump_tmp, key)
        try:
            _create_throwaway_database(config.database_url, throwaway_name)
            _run_pg_restore(pg_restore_bin, throwaway_url, dump_tmp)
            table_counts = _verify_postgres_db(throwaway_url)
        finally:
            _drop_throwaway_database(config.database_url, throwaway_name)
    finally:
        dump_tmp.unlink(missing_ok=True)
    return RestoreTestResult(
        backup_path=enc_path, table_counts=table_counts, throwaway_db_name=throwaway_name
    )


# --- CLI sloj (po uzoru na dentaland.backup_cli) ---------------------------


def _cmd_run(env: Mapping[str, str]) -> int:
    try:
        config = build_config(env)
        enc_path = create_backup(config, env)
    except Exception as exc:  # CLI granica — svaki failure je non-zero exit.
        print(f"Backup nije uspio: {exc}", file=sys.stderr)
        return 1
    print(f"Backup uspješan: {enc_path}")
    return 0


def _cmd_restore_test(env: Mapping[str, str]) -> int:
    try:
        config = build_config(env)
        result = restore_test(config, env)
    except Exception as exc:  # CLI granica — svaki failure je non-zero exit.
        print(f"Restore-test nije uspio: {exc}", file=sys.stderr)
        return 1
    counts = ", ".join(f"{table}={n}" for table, n in result.table_counts.items())
    print(
        f"Restore-test uspješan (restore-ovano, verifikovano, "
        f"privremena baza obrisana): {result.backup_path}"
    )
    print(f"Broj redova po tabeli u testiranoj bazi: {counts}")
    return 0


def _cmd_status(env: Mapping[str, str]) -> int:
    try:
        config = build_config(env)
    except BackupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    last_file = config.cloud_dir / LAST_BACKUP_FILENAME
    if not last_file.exists():
        print("Nema evidencije o uspješnom backupu (last_backup.txt ne postoji).")
        return 0
    try:
        last = datetime.fromisoformat(last_file.read_text().strip())
    except (OSError, ValueError) as exc:
        print(f"Neispravna evidencija zadnjeg backupa ({last_file}): {exc}", file=sys.stderr)
        return 1
    if last.tzinfo is None or last.utcoffset() is None:
        print(f"Evidencija nije timezone-aware ({last_file}).", file=sys.stderr)
        return 1
    age = datetime.now().astimezone() - last
    hours = age.total_seconds() / 3600
    if age > STALE_AFTER:
        print(f"Zadnji uspješan backup: {last.isoformat()}")
        print(f"STARO: stariji od 25h ({hours:.1f} h).")
    else:
        print(f"Zadnji uspješan backup: {last.isoformat()} (OK, {hours:.1f} h).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m dentaland.backup_postgres",
        description="Operativni backup Dentaland PostgreSQL baze (DENT-IMPROVE-016).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Kreiraj enkriptovan pg_dump odmah.")
    sub.add_parser(
        "restore-test",
        help="Restore najnovijeg backupa u privremenu bazu, verifikuj, obriši je.",
    )
    sub.add_parser("status", help="Prikaži status zadnjeg uspješnog backupa.")
    return parser


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    environ = os.environ if env is None else env
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return _cmd_run(environ)
    if args.command == "restore-test":
        return _cmd_restore_test(environ)
    return _cmd_status(environ)


if __name__ == "__main__":
    raise SystemExit(main())
