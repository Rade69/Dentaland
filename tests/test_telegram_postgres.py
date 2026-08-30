"""DENT-IMPROVE-018 — adversarni konkurentni regresioni test za F3
(Codex review, 30.8.2026): dva ISTOVREMENA webhook poziva sa istim
opt-in tokenom ne smiju oba "potrošiti" isti token.

Testovi u ovom fajlu se PRESKAČU (ne FAIL) bez ``DATABASE_URL_TEST``, isti
obrazac kao ``tests/test_postgres_migration.py``. Namjerno koristi
STVARAN Postgres sa ODVOJENIM konekcijama (ne SQLite/``StaticPool`` kao
ostatak ``test_telegram.py``) — SQLite serijalizuje pisanja na nivou
cijele baze, pa ne bi mogao dokazati da je fix stvarno atoman na nivou
reda (Postgres row-level lock preko ``UPDATE ... WHERE``).

**Napomena o metodologiji**: naivan test sa dva threada + ``Barrier``
(pokušano prvo) NIJE pouzdano reprodukovao race čak ni na starom
(pre-fix) kodu — lokalni Postgres round-trip je prebrz, oba threada
skoro uvijek završe sekvencijalno prije nego što bi se stigli
"sudariti". Umjesto oslanjanja na sreću u schedulingu, test ispod
DIREKTNO eksploatiše Postgres-ovo dokumentovano ponašanje: konkurentni
``UPDATE`` na isti red BLOKIRA dok prva transakcija ne commit-uje/
rollback-uje, pa TEK ONDA ponovo evaluira svoj ``WHERE`` protiv
committed stanja. Prva transakcija se namjerno drži otvorenom
(``begin()`` bez ``commit()``) dok druga (u posebnom threadu) ne uđe u
blokirano stanje — determinističko, ne zavisi od brzine mašine.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, update
from sqlalchemy.engine import Engine

from dentaland.models import Appointment, AppointmentStatus, Base, utcnow
from dentaland.services import telegram

DATABASE_URL_TEST = os.environ.get("DATABASE_URL_TEST")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL_TEST,
    reason=(
        "DATABASE_URL_TEST nije postavljen -- konkurentni Telegram token "
        "test se preskace. Standardan `pytest tests/ -q` ostaje SQLite-only."
    ),
)


@pytest.fixture()
def engine() -> Engine:
    assert DATABASE_URL_TEST is not None
    eng = create_engine(DATABASE_URL_TEST, pool_size=5)
    Base.metadata.create_all(eng)
    return eng


def _make_appointment_with_token(engine: Engine, raw_token: str) -> int:
    from sqlalchemy.orm import Session, sessionmaker

    session_factory: sessionmaker[Session] = sessionmaker(bind=engine, expire_on_commit=False)
    start = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
    with session_factory() as session:
        appt = Appointment(
            ime="Konkurentni F3 Test",
            telefon="061",
            start_time=start,
            end_time=start + timedelta(minutes=30),
            status=AppointmentStatus.SCHEDULED,
            telegram_link_token_hash=telegram.hash_token(raw_token),
            telegram_link_token_expires_at=utcnow() + timedelta(hours=1),
            telegram_chat_id=None,
        )
        session.add(appt)
        session.commit()
        return appt.id


def test_atomski_update_blokira_i_ponovo_evaluira_where_pod_konkurencijom(
    engine: Engine,
) -> None:
    """Deterministički dokaz mehanizma na kojem se F3 fix oslanja: A drži
    transakciju otvorenu nakon uspješnog UPDATE-a (ne commit-uje odmah);
    B (poseban thread) pokuša ISTI atomski UPDATE preko
    ``consume_telegram_link_token`` — MORA blokirati (ne odmah vratiti
    ``None`` niti duplo "uspjeti"). Kad A commit-uje, B se odblokira,
    ponovo evaluira WHERE protiv sad-committed stanja (chat_id više NIJE
    NULL), pogađa nula redova, vraća ``None``. Ovo je isti fix koji
    ``test_konkurentni_pokusaji_isti_token_samo_jedan_uspijeva`` provjerava
    kroz stvarnu javnu funkciju — ovaj test dodatno dokazuje DA SE
    blokiranje stvarno dešava, ne samo da je krajnji rezultat ispravan."""
    raw_token = "deterministicki-race-token"
    appt_id = _make_appointment_with_token(engine, raw_token)
    token_hash = telegram.hash_token(raw_token)
    now = utcnow()

    conn_a = engine.connect()
    trans_a = conn_a.begin()
    result_a = conn_a.execute(
        update(Appointment)
        .where(
            Appointment.telegram_link_token_hash == token_hash,
            Appointment.telegram_link_token_expires_at > now,
            Appointment.telegram_chat_id.is_(None),
        )
        .values(telegram_chat_id="A", telegram_subscribed_at=now, telegram_link_token_hash=None)
    )
    assert result_a.rowcount == 1, "A mora uspješno pogoditi red (nema konkurencije još)"
    # A NAMJERNO ne commit-uje ovdje -- drži red zaključan.

    b_outcome: dict[str, object] = {}
    b_started_blocking = threading.Event()

    def run_b() -> None:
        from sqlalchemy.orm import sessionmaker

        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        b_started_blocking.set()  # najbolja aproksimacija "B je počeo" prije poziva
        outcome = telegram.consume_telegram_link_token(session_factory, raw_token, "B")
        b_outcome["result"] = outcome

    thread_b = threading.Thread(target=run_b)
    thread_b.start()
    b_started_blocking.wait(timeout=2)
    # Daj B-u realnu priliku da stigne do blokirajućeg UPDATE-a prije nego
    # što A commit-uje -- ako B nekim čudom već završi (npr. vrati None jer
    # A još nije commit-ovao pa B ne vidi A-ino stanje uopšte, čisto READ
    # COMMITTED ponašanje), thread_b.join ispod će to i dalje ispravno uhvatiti.
    time.sleep(0.3)
    assert thread_b.is_alive(), (
        "B je trebao BLOKIRATI čekajući A-in row lock (dokaz da UPDATE "
        "stvarno zaključava red, ne samo logički provjerava)"
    )

    trans_a.commit()
    conn_a.close()
    thread_b.join(timeout=5)
    assert not thread_b.is_alive(), "B se morao odblokirati nakon A-inog commit-a"

    assert b_outcome["result"] is None, (
        f"B je MORAO vidjeti da je token već potrošen (None), dobijeno: {b_outcome['result']}"
    )

    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        final = session.get(Appointment, appt_id)
        assert final is not None
        assert final.telegram_chat_id == "A", "A je trebao 'pobijediti', B ne smije prepisati"
        session.delete(final)
        session.commit()


def test_konkurentni_pokusaji_isti_token_samo_jedan_uspijeva(engine: Engine) -> None:
    """Crno-kutijski regresioni test kroz stvarnu javnu funkciju (bez
    ručne SQL orkestracije iznad) — dvije stvarne konkurentne niti,
    isti token, provjerava da SAMO jedna uspije. Ovaj test je manje
    determinističan od gornjeg (zavisi od thread scheduling-a da bi
    STVARNO isprobao konkurentan put), ali je bliži stvarnom webhook
    scenariju i ostaje kao dodatna, nezavisna provjera krajnjeg
    ponašanja."""
    from sqlalchemy.orm import Session, sessionmaker

    raw_token = "black-box-race-token"
    appt_id = _make_appointment_with_token(engine, raw_token)
    session_factory: sessionmaker[Session] = sessionmaker(bind=engine, expire_on_commit=False)

    results: list[tuple[str, datetime | None]] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def attempt(chat_id: str) -> None:
        barrier.wait()
        outcome = telegram.consume_telegram_link_token(session_factory, raw_token, chat_id)
        with results_lock:
            results.append((chat_id, outcome))

    t1 = threading.Thread(target=attempt, args=("111",))
    t2 = threading.Thread(target=attempt, args=("222",))
    try:
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        successes = [r for r in results if r[1] is not None]
        assert len(successes) == 1, (
            f"Očekivan TAČNO jedan uspješan konzum tokena, dobijeno: {results}"
        )
    finally:
        with session_factory() as session:
            leftover = session.get(Appointment, appt_id)
            if leftover is not None:
                session.delete(leftover)
                session.commit()
