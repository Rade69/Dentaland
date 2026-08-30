"""DENT-IMPROVE-019 — TZDateTime mora ispravno round-trip-ovati na Postgresu
bez obzira na sesijsku ``TimeZone`` servera.

Testovi u ovom fajlu se PRESKAČU (ne FAIL) bez ``DATABASE_URL_TEST``, isti
obrazac kao ``tests/test_postgres_migration.py`` — standardan
``pytest tests/ -q`` bez postavljene varijable ostaje SQLite-only.

Kritično: konekcija je NAMJERNO postavljena na ne-UTC sesijsku zonu
(``America/New_York``), ne oslanja se na to da je test server slučajno već
UTC — upravo ta slučajnost je sakrila originalni bug (vidi
``agent_reports/DENT-IMPROVE-019-task-contract.md``). Test
``test_round_trip_ne_pomjera_vrijeme_kad_sesija_nije_utc`` je adversarni
regresioni test: dokazano PADA sa starim ``TZDateTime`` (``impl = DateTime``
bez ``timezone=True``), PROLAZI sa fixom — ista metodologija kao
DENT-IMPROVE-013 F1 fix.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import DateTime, create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from dentaland.models import Appointment, AppointmentStatus

DATABASE_URL_TEST = os.environ.get("DATABASE_URL_TEST")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL_TEST,
    reason=(
        "DATABASE_URL_TEST nije postavljen -- TZDateTime Postgres test se "
        "preskace. Standardan `pytest tests/ -q` (bez DATABASE_URL_TEST) "
        "ostaje SQLite-only i identican ranijem ponasanju."
    ),
)

_NON_UTC_SESSION_TZ = "America/New_York"


@pytest.fixture()
def engine() -> Iterator[Engine]:
    assert DATABASE_URL_TEST is not None
    eng = create_engine(
        DATABASE_URL_TEST,
        connect_args={"options": f"-c timezone={_NON_UTC_SESSION_TZ}"},
    )
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_sesija_je_stvarno_ne_utc(engine: Engine) -> None:
    """Sanity-check da fixture stvarno postavlja ne-UTC sesijsku zonu — ako
    ovo padne, ostali testovi u ovom fajlu ne dokazuju ono što tvrde."""
    with engine.connect() as conn:
        tz = conn.execute(text("SHOW TimeZone")).scalar()
    assert tz == _NON_UTC_SESSION_TZ


# Sve TZDateTime kolone na cijelom lancu migracija -- MORA se poklapati
# sa `_TZDATETIME_COLUMNS` u `g7h8i9j0k1l2_tzdatetime_timestamptz.py`.
# Namjerno duplirano (ne dinamički import migracije) -- eksplicitna
# lista ovdje je i sama regresiona zaštita: Codex F1 (30.8.2026) je bio
# tačno to da su dvije DENT-IMPROVE-018 Telegram kolone nedostajale u
# migraciji; ako se ubuduće doda TZDateTime kolona pa zaboravi u
# migraciji, ovaj test to hvata (asertacija na broj kolona ispod).
_ALL_TZDATETIME_COLUMNS: list[tuple[str, str]] = [
    ("time_off", "od_datetime"),
    ("time_off", "do_datetime"),
    ("appointments", "start_time"),
    ("appointments", "end_time"),
    ("appointments", "confirmed_at"),
    ("appointments", "arrived_at"),
    ("appointments", "reminder_sent_at"),
    ("appointments", "created_at"),
    ("appointments", "updated_at"),
    ("appointments", "telegram_link_token_expires_at"),
    ("appointments", "telegram_subscribed_at"),
    ("users", "created_at"),
    ("sessions", "expires_at"),
    ("sessions", "created_at"),
    ("sessions", "revoked_at"),
    ("audit_events", "occurred_at"),
]


def test_migracija_postavlja_timestamptz_na_svih_16_kolona() -> None:
    """alembic upgrade head (stvaran, ne create_all) mora ostaviti SVAKU
    TZDateTime kolonu kao timestamptz, ne timestamp bez zone -- Codex F1
    (30.8.2026): originalna verzija je provjeravala samo 2 od 16 kolona i
    propustila da uhvati da dvije DENT-IMPROVE-018 Telegram kolone
    (dodane paralelnom granom) nisu bile pokrivene."""
    assert DATABASE_URL_TEST is not None
    assert len(_ALL_TZDATETIME_COLUMNS) == 16
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", DATABASE_URL_TEST)
    command.upgrade(config, "head")

    inspect_engine = create_engine(DATABASE_URL_TEST)
    try:
        inspector = inspect(inspect_engine)
        columns_by_table = {
            table: {c["name"]: c for c in inspector.get_columns(table)}
            for table in {t for t, _ in _ALL_TZDATETIME_COLUMNS}
        }
        for table, column in _ALL_TZDATETIME_COLUMNS:
            col_type = columns_by_table[table][column]["type"]
            assert isinstance(col_type, DateTime), f"{table}.{column} nije DateTime tip"
            assert col_type.timezone is True, f"{table}.{column} nije timestamptz"
    finally:
        inspect_engine.dispose()


def test_round_trip_ne_pomjera_vrijeme_kad_sesija_nije_utc(
    session_factory: sessionmaker[Session],
) -> None:
    """Regresioni test za tačan bug otkriven 30.8.2026 (DENT-IMPROVE-018
    end-to-end test): 11:00 UTC upisano mora ostati 11:00 UTC pri čitanju,
    čak i kad je sesijska TimeZone America/New_York."""
    original = datetime(2026, 8, 31, 11, 0, tzinfo=UTC)
    with session_factory() as session:
        new_appt = Appointment(
            ime="DENT-IMPROVE-019 TZ regresioni test",
            telefon="0",
            start_time=original,
            status=AppointmentStatus.PENDING,
        )
        session.add(new_appt)
        session.commit()
        appt_id = new_appt.id

    try:
        with session_factory() as session:
            fetched = session.get(Appointment, appt_id)
            assert fetched is not None
            assert fetched.start_time == original
    finally:
        with session_factory() as session:
            leftover = session.get(Appointment, appt_id)
            if leftover is not None:
                session.delete(leftover)
                session.commit()


def test_round_trip_razliciti_offset_ulaz_i_uvijek_vraca_utc(
    session_factory: sessionmaker[Session],
) -> None:
    """Bilo koji tz-aware ulaz (ne samo +00:00) mora sačuvati apsolutni
    trenutak, i uvijek se vratiti sa UTC tzinfo (docstring garancija)."""
    original = datetime(2026, 8, 31, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    with session_factory() as session:
        new_appt = Appointment(
            ime="DENT-IMPROVE-019 TZ offset test",
            telefon="0",
            start_time=original,
            status=AppointmentStatus.PENDING,
        )
        session.add(new_appt)
        session.commit()
        appt_id = new_appt.id

    try:
        with session_factory() as session:
            fetched = session.get(Appointment, appt_id)
            assert fetched is not None
            assert fetched.start_time == original
            assert fetched.start_time.tzinfo == UTC
    finally:
        with session_factory() as session:
            leftover = session.get(Appointment, appt_id)
            if leftover is not None:
                session.delete(leftover)
                session.commit()
