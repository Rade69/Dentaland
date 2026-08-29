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
import hashlib
import json
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
import psycopg2.errors  # type: ignore[import-untyped]
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

    ``table_counts`` je broj redova po tabeli u PRIVREMENOJ bazi u trenutku
    provjere (prije nego što je obrisana). ``content_digests`` je SHA-256
    otisak stvarnog SADRŽAJA (ne samo broja) redova po tabeli, upoređen sa
    otiskom snimljenim u trenutku backupa (``<backup>.manifest.json``) —
    Codex review F1 round 2 (2026-08-29): isti broj redova sa IZMIJENJENIM
    sadržajem je ranije prolazio kao "verifikovano"; digest to hvata.
    """

    backup_path: Path
    table_counts: dict[str, int]
    content_digests: dict[str, str]
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


def _extract_password(database_url: str) -> str | None:
    """Lozinka može biti u authority dijelu (``user:pass@host``) ILI kao
    ``?password=...`` query parametar (oba su validni libpq oblici) —
    Codex review F1 round 2 (2026-08-29): prva verzija je čitala samo
    authority formu, pa je query-param lozinka i dalje curila u argv.
    """
    url = make_url(database_url)
    if url.password:
        return url.password
    query_password = url.query.get("password")
    return str(query_password) if query_password else None


def _url_without_password(database_url: str) -> str:
    """URL bez lozinke ni u authority dijelu ni u query stringu — bezbjedan
    za argv (proces command-line je vidljiv kroz procesnu
    inspekciju/task manager). Lozinka ide kroz ``PGPASSWORD`` env
    varijablu umjesto toga (vidi ``_pg_subprocess_env``).

    ``URL.set(password=None)`` je NAMJERNO izbjegnut — ``None`` tu znači
    "ne mijenjaj", ne "obriši" (SQLAlchemy sentinel), pa bi tiho ostavio
    lozinku u stringu. ``URL.create()`` bez ``password`` argumenta daje
    čist ``user@host`` (bez dvotačke) za authority formu; query-param
    lozinka se dodatno uklanja preko ``difference_update_query``.
    """
    url = make_url(database_url)
    clean = URL.create(
        drivername=url.drivername,
        username=url.username,
        host=url.host,
        port=url.port,
        database=url.database,
        query=url.query,
    )
    return clean.difference_update_query(["password"]).render_as_string(hide_password=False)


def _pg_subprocess_env(database_url: str) -> dict[str, str]:
    """Environment za pg_dump/pg_restore subprocess.

    UVIJEK puni ``os.environ`` (ne bilo koji ``env`` override mapping) —
    subprocess-u trebaju PATH/SYSTEMROOT i sl. da uopšte radi (npr. DNS
    resolution na Windowsu puca bez njih); override mape koje pozivaoci
    koriste za DENTALAND_* konfiguraciju NISU zamjena za pravi OS
    environment. Dodaje ``PGPASSWORD`` da lozinka ne mora u argv (iz bilo
    kojeg oblika — vidi ``_extract_password``).
    """
    base = dict(os.environ)
    password = _extract_password(database_url)
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
    """Zadrži zadnjih ``daily_keep`` dumpova, obriši ostalo (uklj. manifest
    sidecar fajlove); vrati obrisane."""
    files = _list_backups(config.cloud_dir)
    to_delete = files[config.daily_keep :]
    for path in to_delete:
        path.unlink(missing_ok=True)
        _manifest_path(path).unlink(missing_ok=True)
    return to_delete


def _write_last_backup(cloud_dir: Path, when: datetime) -> None:
    (cloud_dir / LAST_BACKUP_FILENAME).write_text(when.isoformat() + "\n")


def _manifest_path(enc_path: Path) -> Path:
    return enc_path.with_name(enc_path.name + ".manifest.json")


def _rows_digest(rows: list[tuple[object, ...]]) -> str:
    """SHA-256 nad kanonski poređanim SADRŽAJEM redova (ne samo brojem) —
    Codex review F1 round 2 (2026-08-29): isti broj redova sa izmijenjenim
    sadržajem mora dati DRUGAČIJI digest, ne proći kao "identično".
    ``\\x1e``/``\\x1f`` (ASCII record/unit separator) razdvajaju vrijednosti
    da izbjegnu dvosmislenost oko delimitera koji bi se pojavio u samom
    sadržaju (npr. zarez ili pipe unutar imena).
    """
    canonical = "\x1f".join(
        "\x1e".join("" if value is None else repr(value) for value in row) for row in rows
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _compute_manifest(database_url: str) -> tuple[dict[str, int], dict[str, str]]:
    """Poveži se na bazu i za svaku ``CORE_TABLES`` tabelu vrati broj redova
    i sadržajni digest, poređane po ``id`` radi determinizma. Baca sirove
    ``psycopg2`` greške — pozivaoci ih umotavaju u odgovarajući tip greške
    (``BackupError`` na izvoru, ``RestoreVerificationError`` na restore-u).
    """
    conn = psycopg2.connect(database_url)
    try:
        counts: dict[str, int] = {}
        digests: dict[str, str] = {}
        with conn.cursor() as cur:
            for table in CORE_TABLES:
                cur.execute(sql.SQL("SELECT * FROM {} ORDER BY id").format(sql.Identifier(table)))
                rows = cur.fetchall()
                counts[table] = len(rows)
                digests[table] = _rows_digest(rows)
        return counts, digests
    finally:
        conn.close()


def _write_content_manifest(enc_path: Path, digests: dict[str, str]) -> None:
    _manifest_path(enc_path).write_text(json.dumps({"content_digests": digests}, indent=2))


def _read_content_manifest(enc_path: Path) -> dict[str, str]:
    manifest_path = _manifest_path(enc_path)
    if not manifest_path.exists():
        raise BackupError(f"Manifest fajl ne postoji za backup: {manifest_path.name}")
    try:
        data = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        raise BackupError(f"Manifest fajl je neispravan: {manifest_path.name}: {exc}") from exc
    digests = data.get("content_digests")
    if not isinstance(digests, dict):
        raise BackupError(f"Manifest fajl nema 'content_digests': {manifest_path.name}")
    return digests


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


def _create_throwaway_database(admin_url: str, throwaway_name: str) -> None:
    """Kreira privremenu bazu. NAMJERNO bez pre-emptive ``DROP IF EXISTS``.

    Codex review F2 round 2 (2026-08-29): pre-emptive DROP je pretpostavljao
    da svaka baza sa tim imenom mora biti naš stari ostatak — kod kolizije
    (neko drugi/nešto drugo već ima bazu tog imena) to je brisalo tuđi
    objekat. Sad se samo pokušava ``CREATE`` — ako ime već postoji, to je
    greška (kolizija), ne signal da treba obrisati postojeće. Pozivalac
    (``restore_test``) postavlja cleanup-eligible zastavicu TEK nakon što
    ovaj poziv uspije, pa se ``DROP`` u cleanup-u nikad ne poziva nad bazom
    koju ovaj proces nije sam kreirao.
    """
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(throwaway_name)))
            except psycopg2.errors.DuplicateDatabase as exc:
                raise BackupError(
                    f"Privremena baza '{throwaway_name}' već postoji (kolizija imena) — "
                    "odustajem umjesto da je obrišem, nije naša da je brišemo."
                ) from exc
    finally:
        conn.close()


def _drop_throwaway_database(admin_url: str, throwaway_name: str) -> None:
    """Briše privremenu bazu. Pozivalac MORA garantovati da ju je ovaj
    proces stvarno kreirao (vidi ``_create_throwaway_database`` docstring)
    — ova funkcija sama ne provjerava ownership."""
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            stmt = sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(throwaway_name))
            cur.execute(stmt)
    finally:
        conn.close()


def _verify_postgres_db(database_url: str) -> tuple[dict[str, int], dict[str, str]]:
    """Potvrdi da restore-ovana baza ima KOMPLETNU očekivanu šemu i vrati
    (broj redova, sadržajni digest) po tabeli — restore-test-specifičan
    omotač oko ``_compute_manifest`` koji greške pretvara u
    ``RestoreVerificationError``.
    """
    try:
        return _compute_manifest(database_url)
    except psycopg2.OperationalError as exc:
        raise RestoreVerificationError(f"Restore-test baza nije dostupna: {exc}") from exc
    except psycopg2.Error as exc:
        raise RestoreVerificationError(
            f"Restore-test baza nije čitljiva/kompletna: {exc}"
        ) from exc


def _verify_content_matches_manifest(
    enc_path: Path, restored_digests: dict[str, str]
) -> None:
    """Uporedi digest restore-ovane baze sa onim snimljenim u trenutku
    backupa. Codex review F1 round 2 (2026-08-29): isti broj redova sa
    IZMIJENJENIM sadržajem je ranije prolazio kao "identično" — ovo je
    stvaran dokaz sadržaja, ne samo broja.
    """
    expected = _read_content_manifest(enc_path)
    mismatched = [t for t in CORE_TABLES if expected.get(t) != restored_digests.get(t)]
    if mismatched:
        raise RestoreVerificationError(
            "Sadržaj restore-ovane baze se ne poklapa sa backup manifestom "
            f"za tabele: {', '.join(mismatched)}"
        )


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

    # Sadržajni otisak IZVORNE baze u trenutku backupa — restore_test ga
    # kasnije upoređuje sa otiskom restore-ovane baze (Codex F1 round 2).
    try:
        _, digests = _compute_manifest(config.database_url)
    except psycopg2.Error as exc:
        raise BackupError(f"Ne mogu izračunati content manifest izvorne baze: {exc}") from exc
    _write_content_manifest(enc_path, digests)

    rotate_backups(config)
    _write_last_backup(config.cloud_dir, now)
    return enc_path


def restore_test(
    config: PostgresBackupConfig, env: Mapping[str, str] | None = None
) -> RestoreTestResult:
    """Dekriptuj najnoviji backup, restore u PRIVREMENU bazu, verifikuj, obriši je.

    Nikad ne dira ``config.database_url`` bazu samu — koristi se samo kao
    admin konekcija za ``CREATE``/``DROP DATABASE`` privremene test baze.
    Ime privremene baze je jedinstveno po pozivu (``_throwaway_db_name``).
    Cleanup u ``finally`` ispod se poziva SAMO ako je ``_create_throwaway_database``
    stvarno uspjela (``created`` zastavica) — Codex review F2 round 2
    (2026-08-29): bezuslovan cleanup bi kod kolizije imena obrisao tuđu
    bazu; ownership se dokazuje time da je OVAJ proces stvarno kreirao
    bazu, ne pretpostavkom. Kreiranje je unutar istog bloka koji cleanup
    pokriva (Codex F3): pad ODMAH nakon uspješnog ``CREATE DATABASE`` i
    dalje briše ono što je kreirano.
    """
    enc_path = _latest_backup(config.cloud_dir)
    if enc_path is None:
        raise BackupError(f"Nema backupa za testiranje u: {config.cloud_dir}")
    key = load_key(config.key_path)

    pg_restore_bin = _resolve_binary("pg_restore", env)
    dump_tmp = config.local_dir / "restore-test.dump"
    throwaway_name = _throwaway_db_name(config.database_url)
    throwaway_url = _throwaway_url(config.database_url, throwaway_name)
    created = False
    try:
        _decrypt(enc_path, dump_tmp, key)
        try:
            _create_throwaway_database(config.database_url, throwaway_name)
            created = True
            _run_pg_restore(pg_restore_bin, throwaway_url, dump_tmp)
            table_counts, content_digests = _verify_postgres_db(throwaway_url)
            _verify_content_matches_manifest(enc_path, content_digests)
        finally:
            if created:
                _drop_throwaway_database(config.database_url, throwaway_name)
    finally:
        dump_tmp.unlink(missing_ok=True)
    return RestoreTestResult(
        backup_path=enc_path,
        table_counts=table_counts,
        content_digests=content_digests,
        throwaway_db_name=throwaway_name,
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
