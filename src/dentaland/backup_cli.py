"""CLI za operativni backup Dentaland baze (DENT-IMPROVE-007).

Pokretanje (iz korijena repoa, uz ``PYTHONPATH=src``):

    python -m dentaland.backup_cli run
    python -m dentaland.backup_cli restore-test
    python -m dentaland.backup_cli status

``run`` kreira enkriptovan backup kroz postojeći engine
(``dentaland.backup.create_backup``) i vraća non-zero exit kod na bilo koji
failure. ``restore-test`` dekriptuje NAJNOVIJI backup na zasebnu test
destinaciju (nikad preko aktivne baze), verifikuje da je čitljiva SQLite
baza i briše plain test fajl. ``status`` čita ``last_backup.txt`` i prijavljuje
zadnji uspješan backup + "STARO" flag.

Konfiguracija (vidi ``.env.example`` i
``docs/dentaland-backup-operativni-vodic.md``):

- ``DENTALAND_DATA_DIR`` — data folder (default: ``%LOCALAPPDATA%\\Dentaland``);
- ``DENTALAND_BACKUP_CLOUD_DIR`` — cloud/sync folder (default: lokalni
  ``data_dir()/backups``).

Ključ za enkripciju živi u ``data_dir()/config/backup.key`` — izvan lokalnog
i cloud backup foldera.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path

from dentaland import paths
from dentaland.backup import (
    BACKUP_PREFIX,
    BACKUP_SUFFIX,
    LAST_BACKUP_FILENAME,
    BackupConfig,
    BackupError,
    create_backup,
    restore_backup,
)

BACKUP_KEY_FILENAME = "backup.key"
RESTORE_TEST_DIRNAME = "restore-test"
RESTORE_TEST_FILENAME = "dentaland-test.db"
STALE_AFTER = timedelta(hours=25)


def build_config(env: Mapping[str, str] | None = None) -> BackupConfig:
    """Sastavi ``BackupConfig`` iz centralnih putanja i env override-ova."""
    return BackupConfig(
        db_path=paths.database_path(env),
        local_dir=paths.backup_dir(env),
        cloud_dir=paths.backup_cloud_dir(env),
        key_path=paths.config_dir(env) / BACKUP_KEY_FILENAME,
    )


def _latest_backup(cloud_dir: Path) -> Path | None:
    # Imena sadrže zero-padded datum → leksikografski sort = hronološki.
    files = sorted(cloud_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"), reverse=True)
    return files[0] if files else None


def _verify_sqlite_db(path: Path) -> None:
    """Potvrdi da je ``path`` čitljiva SQLite baza sa ``appointments`` tabelom."""
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        if row is None or row[0] != "ok":
            raise BackupError(f"Integrity check nije prošao: {row}")
        # Ako appointments ne postoji, ovo baca sqlite3.Error → BackupError.
        conn.execute("SELECT COUNT(*) FROM appointments").fetchone()
    except sqlite3.Error as exc:
        raise BackupError(f"Restore-test baza nije čitljiva: {exc}") from exc
    finally:
        conn.close()


def _cmd_run(env: Mapping[str, str]) -> int:
    try:
        config = build_config(env)
        enc_path = create_backup(config)
    except Exception as exc:  # CLI granica — svaki failure je non-zero exit.
        print(f"Backup nije uspio: {exc}", file=sys.stderr)
        return 1
    print(f"Backup uspješan: {enc_path}")
    return 0


def _cmd_restore_test(env: Mapping[str, str]) -> int:
    try:
        config = build_config(env)
        enc_path = _latest_backup(config.cloud_dir)
        if enc_path is None:
            print(f"Nema backupa za testiranje u: {config.cloud_dir}", file=sys.stderr)
            return 1
        dest = paths.data_dir(env) / RESTORE_TEST_DIRNAME / RESTORE_TEST_FILENAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            restore_backup(config, enc_path, dest)
            _verify_sqlite_db(dest)
        finally:
            # Plain test .db je privremen — nikad ne ostaje na disku.
            dest.unlink(missing_ok=True)
        print(f"Restore-test uspješan (dekriptovano i verifikovano): {enc_path}")
        return 0
    except Exception as exc:  # CLI granica — svaki failure je non-zero exit.
        print(f"Restore-test nije uspio: {exc}", file=sys.stderr)
        return 1


def _cmd_status(env: Mapping[str, str]) -> int:
    config = build_config(env)
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
        prog="python -m dentaland.backup_cli",
        description="Operativni backup Dentaland baze (DENT-IMPROVE-007).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Kreiraj enkriptovan backup odmah.")
    sub.add_parser(
        "restore-test",
        help="Dekriptuj i verifikuj najnoviji backup na zasebnu destinaciju.",
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
