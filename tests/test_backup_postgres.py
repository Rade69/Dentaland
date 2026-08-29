"""Testovi za PostgreSQL backup (DENT-IMPROVE-016).

Test se PRESKAČE (ne FAIL) ako ``DATABASE_URL_TEST`` env var nije
postavljen — isti obrazac kao ``tests/test_postgres_migration.py``.
Standardan ``pytest tests/ -q`` (bez te varijable) ostaje nepromijenjen.

Radi protiv izolovane LOKALNE Dentaland Postgres instance (port 5433,
vidi ``.env``), NIKAD produkcijske baze. Marker-tagovani redovi (isti
obrazac kao ``test_postgres_migration.py``) se briše u teardown-u.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg2
import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from dentaland.backup import BackupError
from dentaland.backup_postgres import (
    BACKUP_PREFIX,
    BACKUP_SUFFIX,
    LAST_BACKUP_FILENAME,
    RESTORE_TEST_DB_SUFFIX,
    PostgresBackupConfig,
    build_config,
    create_backup,
    main,
    restore_test,
)
from dentaland.models import Base, Doctor

DATABASE_URL_TEST = os.environ.get("DATABASE_URL_TEST")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL_TEST,
    reason=(
        "DATABASE_URL_TEST nije postavljen -- Postgres backup test se preskace. "
        "Standardan `pytest tests/ -q` (bez DATABASE_URL_TEST) ostaje nepromijenjen."
    ),
)

_MARKER = "Backup Postgres Test"
_DOCTOR_NAME = f"Test Doktor {_MARKER}"


def _cleanup(session: Session) -> None:
    session.execute(delete(Doctor).where(Doctor.ime == _DOCTOR_NAME))
    session.commit()


@pytest.fixture()
def pg_engine() -> Iterator[Engine]:
    assert DATABASE_URL_TEST is not None
    eng = create_engine(DATABASE_URL_TEST)
    Base.metadata.create_all(eng)  # no-op ako je alembic upgrade head vec primijenjen
    yield eng
    eng.dispose()


@pytest.fixture()
def pg_session_factory(pg_engine: Engine) -> Iterator[sessionmaker[Session]]:
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    with factory() as session:
        _cleanup(session)  # cist pocetak i ako je prethodni run pukao prije teardown-a
        session.add(Doctor(ime=_DOCTOR_NAME))
        session.commit()
    yield factory
    with factory() as session:
        _cleanup(session)


@pytest.fixture()
def config(tmp_path: Path, pg_session_factory: sessionmaker[Session]) -> PostgresBackupConfig:
    assert DATABASE_URL_TEST is not None
    return PostgresBackupConfig(
        database_url=DATABASE_URL_TEST,
        local_dir=tmp_path / "backups" / "postgres",
        cloud_dir=tmp_path / "backups" / "postgres",
        key_path=tmp_path / "config" / "backup_postgres.key",
    )


def test_run_pa_restore_test_uspijeva_i_ne_ostavlja_privremenu_bazu(
    config: PostgresBackupConfig,
) -> None:
    enc_path = create_backup(config)

    assert enc_path.exists()
    assert enc_path.name.startswith(BACKUP_PREFIX)
    assert enc_path.name.endswith(BACKUP_SUFFIX)
    assert not (config.local_dir / "backup-tmp.dump").exists()

    restored_path = restore_test(config)

    assert restored_path == enc_path
    assert not (config.local_dir / "restore-test.dump").exists()

    # Privremena test baza je stvarno obrisana, ne samo "izgleda ok".
    throwaway_name = make_url(config.database_url).database + RESTORE_TEST_DB_SUFFIX
    throwaway_url = make_url(config.database_url).set(database=throwaway_name).render_as_string(
        hide_password=False
    )
    with pytest.raises(psycopg2.OperationalError):
        conn = psycopg2.connect(throwaway_url)
        conn.close()


def test_restore_test_ne_dira_aktivnu_bazu(
    config: PostgresBackupConfig,
    pg_session_factory: sessionmaker[Session],
) -> None:
    create_backup(config)

    restore_test(config)

    with pg_session_factory() as session:
        assert session.query(Doctor).filter_by(ime=_DOCTOR_NAME).count() == 1


def test_restore_test_bez_backupa_baca_gresku(config: PostgresBackupConfig) -> None:
    with pytest.raises(BackupError, match="Nema backupa"):
        restore_test(config)


def test_rotacija_zadrzava_samo_daily_keep(config: PostgresBackupConfig) -> None:
    config.daily_keep = 2
    for _ in range(4):
        create_backup(config)

    files = sorted(config.cloud_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))
    assert len(files) == 1  # isto ime svaki put (isti dan) -> overwrite, ne akumulacija


def test_build_config_bez_database_url_baca_gresku() -> None:
    with pytest.raises(BackupError, match="DATABASE_URL"):
        build_config({})


def test_cli_run_pa_restore_test_pa_status(tmp_path: Path) -> None:
    assert DATABASE_URL_TEST is not None
    env = {
        "DATABASE_URL": DATABASE_URL_TEST,
        "DENTALAND_DATA_DIR": str(tmp_path),
    }

    assert main(["run"], env=env) == 0
    assert main(["restore-test"], env=env) == 0

    status_result = main(["status"], env=env)
    assert status_result == 0

    last_file = tmp_path / "backups" / "postgres" / LAST_BACKUP_FILENAME
    assert last_file.exists()
