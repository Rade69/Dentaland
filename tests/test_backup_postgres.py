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

from dentaland import backup_postgres as bp
from dentaland.backup import BackupError
from dentaland.backup_postgres import (
    BACKUP_PREFIX,
    BACKUP_SUFFIX,
    LAST_BACKUP_FILENAME,
    RESTORE_TEST_DB_SUFFIX,
    PostgresBackupConfig,
    RestoreVerificationError,
    _create_throwaway_database,
    _decrypt,
    _drop_throwaway_database,
    _resolve_binary,
    _run_pg_dump,
    _run_pg_restore,
    _verify_content_matches_manifest,
    _verify_postgres_db,
    build_config,
    create_backup,
    load_key,
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

    result = restore_test(config)

    assert result.backup_path == enc_path
    assert not (config.local_dir / "restore-test.dump").exists()
    # Ime je jedinstveno po pozivu (Codex F2), ne isto svaki put.
    assert result.throwaway_db_name.startswith(
        make_url(config.database_url).database + RESTORE_TEST_DB_SUFFIX
    )

    # Privremena test baza je stvarno obrisana, ne samo "izgleda ok".
    throwaway_url = (
        make_url(config.database_url)
        .set(database=result.throwaway_db_name)
        .render_as_string(hide_password=False)
    )
    with pytest.raises(psycopg2.OperationalError):
        conn = psycopg2.connect(throwaway_url)
        conn.close()


def test_restore_test_manifest_odgovara_izvornoj_bazi(
    config: PostgresBackupConfig,
    pg_session_factory: sessionmaker[Session],
) -> None:
    """Regresija za Codex F1 — manifest mora pokazati STVARAN broj redova
    restore-ovane baze, ne samo da je proces uspio."""
    with pg_session_factory() as session:
        source_doctor_count = session.query(Doctor).count()

    create_backup(config)
    result = restore_test(config)

    assert result.table_counts["doctors"] == source_doctor_count
    assert source_doctor_count >= 1  # sanity - fixture je stvarno seedovala marker doktora
    assert set(result.table_counts) >= {"doctors", "appointments", "users", "audit_events"}


def test_verify_odbija_nepotpunu_semu(config: PostgresBackupConfig) -> None:
    """Adversarna regresija za Codex F1: baza sa SAMO praznom ``appointments``
    tabelom (bez ostatka Dentaland šeme) mora pasti verifikaciju, ne proći
    kao 'restore uspio'."""
    fake_name = f"{make_url(config.database_url).database}_fake_incomplete_schema_check"
    _create_throwaway_database(config.database_url, fake_name)
    fake_url = (
        make_url(config.database_url).set(database=fake_name).render_as_string(hide_password=False)
    )
    try:
        conn = psycopg2.connect(fake_url)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE appointments (id integer)")
        finally:
            conn.close()

        with pytest.raises(RestoreVerificationError):
            _verify_postgres_db(fake_url)
    finally:
        _drop_throwaway_database(config.database_url, fake_name)


def test_restore_test_prolazi_i_kad_se_izvorna_baza_promijeni_poslije_backupa(
    config: PostgresBackupConfig,
    pg_session_factory: sessionmaker[Session],
) -> None:
    """Regresija za Codex F1 round 3
    (VALID_DUMP_REJECTED_AFTER_CONCURRENT_POST_DUMP_WRITE): upis u IZVORNU
    bazu NAKON ``create_backup`` ne smije uzrokovati lažan mismatch —
    manifest se računa iz restore-a SAMOG dumpa (vidi ``create_backup``
    docstring), ne iz žive baze poslije dump-a."""
    create_backup(config)

    naknadno_ime = f"{_DOCTOR_NAME} Naknadno Dodat Poslije Backupa"
    with pg_session_factory() as session:
        session.add(Doctor(ime=naknadno_ime))
        session.commit()

    try:
        result = restore_test(config)  # validan backup MORA proći uprkos naknadnom upisu
        assert result.table_counts["doctors"] >= 1
    finally:
        with pg_session_factory() as session:
            session.execute(delete(Doctor).where(Doctor.ime == naknadno_ime))
            session.commit()


def test_restore_hvata_izmijenjen_sadrzaj_uz_isti_broj_redova(
    config: PostgresBackupConfig,
    pg_session_factory: sessionmaker[Session],
) -> None:
    """Adversarna regresija za Codex F1 round 2
    (DIFFERENT_DATA_SAME_MANIFEST_ACCEPTED): restore-uje pravi backup u
    privremenu bazu, pa RUČNO izmijeni sadržaj bez promjene broja redova —
    manifest poređenje mora ovo uhvatiti, ne samo brojanje redova."""
    enc_path = create_backup(config)

    tampered_name = f"{make_url(config.database_url).database}_tampered_content_check"
    _create_throwaway_database(config.database_url, tampered_name)
    tampered_url = (
        make_url(config.database_url)
        .set(database=tampered_name)
        .render_as_string(hide_password=False)
    )
    try:
        pg_restore_bin = _resolve_binary("pg_restore", None)
        dump_tmp = config.local_dir / "tampered-restore-check.dump"
        key = load_key(config.key_path)
        try:
            _decrypt(enc_path, dump_tmp, key)
            _run_pg_restore(pg_restore_bin, tampered_url, dump_tmp)
        finally:
            dump_tmp.unlink(missing_ok=True)

        conn = psycopg2.connect(tampered_url)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE doctors SET ime = 'Izmijenjeno bez promjene broja redova'")
        finally:
            conn.close()

        _, tampered_digests = _verify_postgres_db(tampered_url)
        with pytest.raises(RestoreVerificationError):
            _verify_content_matches_manifest(enc_path, tampered_digests)
    finally:
        _drop_throwaway_database(config.database_url, tampered_name)


def test_create_throwaway_ne_brise_postojecu_bazu_kod_kolizije(
    config: PostgresBackupConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adversarna regresija za Codex F2 round 2
    (EXISTING_DB_WAS_DROPPED_AND_RECREATED): ako ime koje je
    ``_throwaway_db_name`` generisala VEĆ postoji (kolizija), taj proces
    mora odustati sa greškom, ne obrisati i rekreirati postojeću bazu."""
    # Napravi backup PRIJE monkeypatch-a - create_backup interno takodje
    # zove _throwaway_db_name (F1 manifest-iz-dumpa mehanizam), pa mora
    # koristiti nasumicno ime, ne kolidujuce, da se ne pomijesa sa onim
    # sto ovaj test stvarno proverava (restore_test kolizija).
    create_backup(config)

    colliding_name = f"{make_url(config.database_url).database}{RESTORE_TEST_DB_SUFFIX}_kolizija"
    monkeypatch.setattr(
        "dentaland.backup_postgres._throwaway_db_name", lambda database_url: colliding_name
    )

    # Simulira da baza VEC postoji (npr. tuđa) prije nego što restore_test krene.
    _create_throwaway_database(config.database_url, colliding_name)
    colliding_url = (
        make_url(config.database_url)
        .set(database=colliding_name)
        .render_as_string(hide_password=False)
    )
    conn = psycopg2.connect(colliding_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE ownership_sentinel (id integer)")
    finally:
        conn.close()

    try:
        with pytest.raises(BackupError, match="kolizija"):
            restore_test(config)

        # Sentinel MORA i dalje postojati — kolizija ne smije obrisati postojeću bazu.
        conn = psycopg2.connect(colliding_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM ownership_sentinel")
                assert cur.fetchone()[0] == 0
        finally:
            conn.close()
    finally:
        _drop_throwaway_database(config.database_url, colliding_name)


def test_create_throwaway_samocisti_kad_connection_close_pukne_nakon_create(
    config: PostgresBackupConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adversarna regresija za Codex F3 round 3
    (ORIGINAL_POST_CREATE_FAILURE_LEFT_DB): simulira da ``CREATE DATABASE``
    uspije server-side, ali da ``conn.close()`` (post-CREATE cleanup korak
    UNUTAR ``_create_throwaway_database``) pukne prije nego što funkcija
    uredno vrati — baza ne smije preživjeti.

    ``psycopg2`` konekcija je C-extension objekat — ``close`` se ne može
    monkeypatch-ovati direktno na instanci (read-only atribut), pa se
    koristi tanak proxy koji delegira sve OSIM ``close()``.
    """
    throwaway_name = f"{make_url(config.database_url).database}{RESTORE_TEST_DB_SUFFIX}_f3r3"

    class _FlakyCloseConnProxy:
        def __init__(self, real_conn: object) -> None:
            self._real = real_conn

        def cursor(self, *args: object, **kwargs: object) -> object:
            return self._real.cursor(*args, **kwargs)  # type: ignore[attr-defined]

        @property
        def autocommit(self) -> bool:
            return self._real.autocommit  # type: ignore[attr-defined]

        @autocommit.setter
        def autocommit(self, value: bool) -> None:
            self._real.autocommit = value  # type: ignore[attr-defined]

        def close(self) -> None:
            self._real.close()  # type: ignore[attr-defined]
            raise RuntimeError("simulirani pad conn.close() odmah nakon uspješnog CREATE")

    real_connect = bp.psycopg2.connect
    call_count = {"n": 0}

    def _connect_prva_konekcija_ima_flaky_close(*args: object, **kwargs: object) -> object:
        call_count["n"] += 1
        real_conn = real_connect(*args, **kwargs)
        if call_count["n"] == 1:  # prva konekcija = ona unutar _create_throwaway_database
            return _FlakyCloseConnProxy(real_conn)
        return real_conn

    monkeypatch.setattr(bp.psycopg2, "connect", _connect_prva_konekcija_ima_flaky_close)

    with pytest.raises(RuntimeError, match="simulirani pad"):
        bp._create_throwaway_database(config.database_url, throwaway_name)

    throwaway_url = (
        make_url(config.database_url)
        .set(database=throwaway_name)
        .render_as_string(hide_password=False)
    )
    with pytest.raises(psycopg2.OperationalError):
        conn = psycopg2.connect(throwaway_url)
        conn.close()


@pytest.mark.parametrize(
    "url_template",
    [
        "postgresql://neko:{password}@localhost:5433/dentaland_test",
        "postgresql://neko@localhost:5433/dentaland_test?password={password}",
    ],
    ids=["authority-forma", "query-param-forma"],
)
def test_pg_dump_i_restore_ne_stavljaju_lozinku_u_argv_ni_jednim_oblikom(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, url_template: str
) -> None:
    """Regresija za Codex F4 round 2 (QUERY_PASSWORD_IN_ARGV=True): lozinka
    ne smije u argv ni kad je u authority dijelu URL-a ni kad je
    ``?password=...`` query parametar — provjereno za OBA subprocess puta
    (``pg_dump`` i ``pg_restore``)."""
    password = "TajnaLozinkaZaTest456"
    url = url_template.format(password=password)
    captured: list[dict[str, object]] = []

    def _fake_run(cmd: list[str], capture_output: bool, text: bool, env: dict[str, str]):
        captured.append({"cmd": cmd, "env": env})

        class _Result:
            returncode = 0
            stderr = ""

        return _Result()

    monkeypatch.setattr("dentaland.backup_postgres.subprocess.run", _fake_run)

    _run_pg_dump("pg_dump", url, tmp_path / "out.dump")
    _run_pg_restore("pg_restore", url, tmp_path / "out.dump")

    assert len(captured) == 2
    for call in captured:
        cmd = call["cmd"]
        assert isinstance(cmd, list)
        assert password not in " ".join(cmd)
        env = call["env"]
        assert isinstance(env, dict)
        assert env.get("PGPASSWORD") == password


def test_restore_test_cisti_i_kad_pukne_odmah_nakon_create(
    config: PostgresBackupConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regresija za Codex F3: ako nešto pukne ODMAH nakon uspješnog
    CREATE DATABASE (prije restore/verify), privremena baza i dalje mora
    biti obrisana — ne smije preživjeti izuzetak na toj granici."""
    create_backup(config)

    fixed_name = f"{make_url(config.database_url).database}{RESTORE_TEST_DB_SUFFIX}_f3_regresija"
    monkeypatch.setattr(
        "dentaland.backup_postgres._throwaway_db_name", lambda database_url: fixed_name
    )

    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulirani pad odmah nakon CREATE DATABASE")

    monkeypatch.setattr("dentaland.backup_postgres._run_pg_restore", _boom)

    with pytest.raises(RuntimeError, match="simulirani pad"):
        restore_test(config)

    fixed_url = (
        make_url(config.database_url).set(database=fixed_name).render_as_string(hide_password=False)
    )
    with pytest.raises(psycopg2.OperationalError):
        conn = psycopg2.connect(fixed_url)
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
