"""Testovi FastAPI backend-a za javne zahtjeve (DENT-007)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app, get_session_factory, limiter
from dentaland.models import Appointment, AppointmentStatus, Base, Doctor, Service, User, UserRole
from dentaland.services.auth import hash_password
from dentaland.services.notifications import (
    REMINDER_LEAD_TIME,
    REMINDER_WINDOW,
    send_due_appointment_reminders,
)


@pytest.fixture()
def engine() -> Engine:
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def client(session_factory: sessionmaker[Session]):
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    # `limiter` je modul-nivo singleton dijeljen preko cijele pytest sesije —
    # bez reset-a bi kvota potrošena u jednom testu (npr. namjerno-iscrpljujući
    # rate-limit test) curila u naredne testove/fajlove.
    limiter.reset()
    # base_url="https://..." — DENT-IMPROVE-013 login cookie je `Secure`;
    # httpx-ov cookie jar ne šalje `Secure` kolačiće nazad na plain `http://`
    # vezu (standardan obrazac za testiranje secure cookieja kroz TestClient).
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def reception_session(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    """DENT-IMPROVE-013 — `GET /api/booking-requests`, `.../confirm`,
    `.../reject` sada zahtijevaju `RECEPTION` ulogu. Testovi koji ih pozivaju
    prvo se moraju ulogovati; sesioni kolačić ostaje vezan za `client` (isti
    `TestClient` dijeli cookie jar preko svih poziva u tom testu)."""
    with session_factory() as session:
        session.add(
            User(
                username="sestra-test",
                password_hash=hash_password("test-lozinka-123"),
                role=UserRole.RECEPTION,
            )
        )
        session.commit()
    response = client.post(
        "/api/auth/login",
        json={"username": "sestra-test", "password": "test-lozinka-123"},
    )
    assert response.status_code == 200


@pytest.fixture()
def doctor_and_service(session_factory: sessionmaker[Session]) -> tuple[int, int]:
    with session_factory() as session:
        doctor = Doctor(ime="Ljubo")
        service = Service(naziv="Kontrola", trajanje_min=30, buffer_min=0)
        session.add_all([doctor, service])
        session.commit()
        return doctor.id, service.id


def test_submit_booking_request_vraca_201_i_id(client: TestClient) -> None:
    response = client.post(
        "/api/booking-requests",
        json={
            "ime": "Ana Anić",
            "telefon": "061/111-222",
            "email": "ana@x.com",
            "requested_date": "2026-08-20",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert isinstance(body["id"], int)


def test_submit_sa_emailom_ne_pada_kad_smtp_pukne(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DENTALAND_SMTP_HOST", "smtp.example.com")
    with patch(
        "dentaland.services.notifications.smtplib.SMTP", side_effect=OSError("konekcija pala")
    ):
        response = client.post(
            "/api/booking-requests",
            json={
                "ime": "Ana Anić",
                "telefon": "061/111-222",
                "email": "ana@x.com",
                "requested_date": "2026-08-20",
            },
        )
    assert response.status_code == 201


def test_submit_bez_imena_vraca_422(client: TestClient) -> None:
    response = client.post(
        "/api/booking-requests",
        json={"ime": "", "telefon": "061", "requested_date": "2026-08-20"},
    )
    assert response.status_code == 422


def test_get_pending_lista_podnesene_zahtjeve(
    client: TestClient, reception_session: None
) -> None:
    client.post(
        "/api/booking-requests",
        json={"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"},
    )
    response = client.get("/api/booking-requests")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["ime"] == "Ana"


def test_confirm_uspjesno_vraca_204(
    client: TestClient, doctor_and_service: tuple[int, int], reception_session: None
) -> None:
    doctor_id, service_id = doctor_and_service
    submit = client.post(
        "/api/booking-requests",
        json={"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"},
    )
    request_id = submit.json()["id"]

    response = client.post(
        f"/api/booking-requests/{request_id}/confirm",
        json={
            "doctor_id": doctor_id,
            "service_id": service_id,
            "start_time": datetime(2026, 8, 20, 9, 0, tzinfo=UTC).isoformat(),
        },
    )
    assert response.status_code == 204

    pending = client.get("/api/booking-requests").json()
    assert pending == []


def test_confirm_preklapanje_vraca_409(
    client: TestClient,
    session_factory: sessionmaker[Session],
    doctor_and_service: tuple[int, int],
    reception_session: None,
) -> None:
    from dentaland.models import Appointment, AppointmentStatus

    doctor_id, service_id = doctor_and_service
    with session_factory() as session:
        session.add(
            Appointment(
                doctor_id=doctor_id,
                service_id=service_id,
                ime="Postojeci",
                start_time=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
                end_time=datetime(2026, 8, 20, 9, 30, tzinfo=UTC),
                status=AppointmentStatus.SCHEDULED,
            )
        )
        session.commit()

    submit = client.post(
        "/api/booking-requests",
        json={"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"},
    )
    request_id = submit.json()["id"]

    response = client.post(
        f"/api/booking-requests/{request_id}/confirm",
        json={
            "doctor_id": doctor_id,
            "service_id": service_id,
            "start_time": datetime(2026, 8, 20, 9, 15, tzinfo=UTC).isoformat(),
        },
    )
    assert response.status_code == 409


def test_confirm_nepostojeceg_vraca_404(
    client: TestClient, doctor_and_service: tuple[int, int], reception_session: None
) -> None:
    doctor_id, service_id = doctor_and_service
    response = client.post(
        "/api/booking-requests/999/confirm",
        json={
            "doctor_id": doctor_id,
            "service_id": service_id,
            "start_time": datetime(2026, 8, 20, 9, 0, tzinfo=UTC).isoformat(),
        },
    )
    assert response.status_code == 404


def test_reject_uspjesno_vraca_204(client: TestClient, reception_session: None) -> None:
    submit = client.post(
        "/api/booking-requests",
        json={"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"},
    )
    request_id = submit.json()["id"]

    response = client.post(f"/api/booking-requests/{request_id}/reject")
    assert response.status_code == 204
    assert client.get("/api/booking-requests").json() == []


def test_reject_nepostojeceg_vraca_404(client: TestClient, reception_session: None) -> None:
    response = client.post("/api/booking-requests/999/reject")
    assert response.status_code == 404


# ---- GET /api/doctors, GET /api/services (DENT-IMPROVE-020) ----


def test_get_doctors_bez_prijave_vraca_401(client: TestClient) -> None:
    response = client.get("/api/doctors")
    assert response.status_code == 401


def test_get_doctors_vraca_samo_aktivne(
    client: TestClient,
    session_factory: sessionmaker[Session],
    reception_session: None,
) -> None:
    with session_factory() as session:
        session.add_all(
            [
                Doctor(ime="Aktivan Doktor", aktivan=True),
                Doctor(ime="Neaktivan Doktor", aktivan=False),
            ]
        )
        session.commit()

    response = client.get("/api/doctors")
    assert response.status_code == 200
    names = {d["ime"] for d in response.json()}
    assert names == {"Aktivan Doktor"}


def test_get_services_bez_prijave_vraca_401(client: TestClient) -> None:
    response = client.get("/api/services")
    assert response.status_code == 401


def test_get_services_vraca_trajanje_i_buffer(
    client: TestClient,
    session_factory: sessionmaker[Session],
    reception_session: None,
) -> None:
    with session_factory() as session:
        session.add(Service(naziv="Kontrola", trajanje_min=30, buffer_min=5))
        session.commit()

    response = client.get("/api/services")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["naziv"] == "Kontrola"
    assert body[0]["trajanje_min"] == 30
    assert body[0]["buffer_min"] == 5


def test_rate_limit_na_submit_endpointu(client: TestClient) -> None:
    payload = {"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"}
    statuses = [client.post("/api/booking-requests", json=payload).status_code for _ in range(11)]
    assert 429 in statuses, "11. zahtjev u minuti treba da bude odbijen (limit 10/minute)"


def test_rate_limit_na_get_pending_endpointu(client: TestClient, reception_session: None) -> None:
    statuses = [client.get("/api/booking-requests").status_code for _ in range(31)]
    assert 429 in statuses, "31. get_pending zahtjev u minuti treba biti odbijen (limit 30/minute)"


def test_rate_limit_na_confirm_endpointu(
    client: TestClient, doctor_and_service: tuple[int, int], reception_session: None
) -> None:
    doctor_id, service_id = doctor_and_service
    payload = {
        "doctor_id": doctor_id,
        "service_id": service_id,
        "start_time": datetime(2026, 8, 20, 9, 0, tzinfo=UTC).isoformat(),
    }
    statuses = [
        client.post("/api/booking-requests/999/confirm", json=payload).status_code
        for _ in range(21)
    ]
    assert 429 in statuses, "21. confirm zahtjev u minuti treba biti odbijen (limit 20/minute)"


def test_rate_limit_na_reject_endpointu(client: TestClient, reception_session: None) -> None:
    statuses = [client.post("/api/booking-requests/999/reject").status_code for _ in range(21)]
    assert 429 in statuses, "21. reject zahtjev u minuti treba biti odbijen (limit 20/minute)"


def test_scheduler_bira_samo_scheduled_termine_u_uskom_prozoru(
    session_factory: sessionmaker[Session], doctor_and_service: tuple[int, int]
) -> None:
    now = datetime(2026, 8, 20, 8, 0, tzinfo=UTC)
    doctor_id, service_id = doctor_and_service

    def appointment(offset: timedelta, *, status: AppointmentStatus) -> Appointment:
        start = now + offset
        return Appointment(
            doctor_id=doctor_id,
            service_id=service_id,
            ime=f"Pacijent {offset}",
            email=f"pacijent-{int(offset.total_seconds())}@example.com",
            start_time=start,
            end_time=start + timedelta(minutes=30),
            status=status,
        )

    due_at_start = appointment(REMINDER_LEAD_TIME, status=AppointmentStatus.SCHEDULED)
    due_inside = appointment(
        REMINDER_LEAD_TIME + REMINDER_WINDOW - timedelta(seconds=1),
        status=AppointmentStatus.SCHEDULED,
    )
    too_early = appointment(
        REMINDER_LEAD_TIME - timedelta(seconds=1), status=AppointmentStatus.SCHEDULED
    )
    too_late = appointment(
        REMINDER_LEAD_TIME + REMINDER_WINDOW, status=AppointmentStatus.SCHEDULED
    )
    cancelled = appointment(REMINDER_LEAD_TIME, status=AppointmentStatus.CANCELLED)

    with session_factory() as session:
        session.add_all([due_at_start, due_inside, too_early, too_late, cancelled])
        session.commit()

    with patch("dentaland.services.notifications.send_appointment_reminder") as send:
        count = send_due_appointment_reminders(session_factory, now=now)

    assert count == 2
    assert send.call_count == 2
    sent_addresses = {call.args[0] for call in send.call_args_list}
    assert sent_addresses == {due_at_start.email, due_inside.email}


def test_scheduler_ne_salje_dvaput_isti_termin(
    session_factory: sessionmaker[Session], doctor_and_service: tuple[int, int]
) -> None:
    """DENT-022 — restart/dvostruko pokretanje scheduler-a ne smije duplirati slanje."""
    now = datetime(2026, 8, 20, 8, 0, tzinfo=UTC)
    doctor_id, service_id = doctor_and_service
    # Namjerno unutar presjeka oba prozora (ne na granici) — Codex review
    # (2026-08-23) je pokazao da termin tačno na `now + REMINDER_LEAD_TIME`
    # ispada iz drugog, za 1min pomjerenog prozora, pa test u tom slučaju
    # ne provjerava dedup filter, nego samo prirodni pomak prozora.
    start = now + REMINDER_LEAD_TIME + timedelta(minutes=5)

    appt = Appointment(
        doctor_id=doctor_id,
        service_id=service_id,
        ime="Pacijent",
        email="pacijent@example.com",
        start_time=start,
        end_time=start + timedelta(minutes=30),
        status=AppointmentStatus.SCHEDULED,
    )
    with session_factory() as session:
        session.add(appt)
        session.commit()
        appt_id = appt.id

    with patch("dentaland.services.notifications.send_appointment_reminder") as send:
        first = send_due_appointment_reminders(session_factory, now=now)
        # Isti (ili blago pomjeren, i dalje preklapajući) prozor — simulira
        # restart scheduler-a koji ponovo računa "now" od trenutnog vremena.
        second = send_due_appointment_reminders(
            session_factory, now=now + timedelta(minutes=1)
        )

    assert first == 1
    assert second == 0
    assert send.call_count == 1

    with session_factory() as session:
        stored = session.get(Appointment, appt_id)
        assert stored is not None
        assert stored.reminder_sent_at is not None


def test_scheduler_paralelno_pokretanje_ne_salje_dvaput(tmp_path: Path) -> None:
    """DENT-022 — dva paralelna scheduler procesa (dvije nezavisne
    konekcije/thread-a na istoj file-backed SQLite bazi) smiju poslati
    podsjetnik SAMO jednom.

    Replicira Codex-ov adversarni scenario (review, 2026-08-23, REJECT
    runda 1) koji je na prethodnoj implementaciji (SELECT pa slanje pa
    update) dokazao ``CONCURRENT_SEND_COUNT 2`` — obje sesije su pročitale
    ``reminder_sent_at IS NULL`` prije nego što je ijedna commitovala.
    Ovaj test koristi pravu file-backed bazu (ne ``StaticPool``/jedna
    dijeljena konekcija, koja bi trivijalno serijalizovala pristup i
    sakrila bag) i barijeru koja oba threada pušta u isto vrijeme.
    """
    db_path = tmp_path / "dedup-race.db"
    db_url = f"sqlite:///{db_path}"

    setup_engine = create_engine(db_url)
    Base.metadata.create_all(setup_engine)
    setup_engine.dispose()

    now = datetime(2026, 8, 20, 8, 0, tzinfo=UTC)
    start = now + REMINDER_LEAD_TIME + timedelta(minutes=5)

    seed_engine = create_engine(db_url)
    with sessionmaker(bind=seed_engine)() as session:
        doctor = Doctor(ime="Ljubo")
        service = Service(naziv="Kontrola", trajanje_min=30, buffer_min=0)
        session.add_all([doctor, service])
        session.commit()
        appt = Appointment(
            doctor_id=doctor.id,
            service_id=service.id,
            ime="Pacijent",
            email="pacijent@example.com",
            start_time=start,
            end_time=start + timedelta(minutes=30),
            status=AppointmentStatus.SCHEDULED,
        )
        session.add(appt)
        session.commit()
    seed_engine.dispose()

    # Dvije NEZAVISNE konekcije ka ISTOJ file-backed bazi — simulira dva
    # odvojena scheduler procesa (restart preklopljen sa starim procesom,
    # ili slučajno dvostruko pokretanje).
    factory_a = sessionmaker(bind=create_engine(db_url))
    factory_b = sessionmaker(bind=create_engine(db_url))

    barrier = threading.Barrier(2)
    lock = threading.Lock()
    send_calls: list[str] = []

    def fake_send(to_email: str, start_time: datetime) -> None:
        with lock:
            send_calls.append(to_email)

    results: dict[str, int] = {}

    def worker(name: str, factory: sessionmaker[Session]) -> None:
        barrier.wait()  # oba threada pokušavaju u isto vrijeme
        results[name] = send_due_appointment_reminders(factory, now=now)

    with patch(
        "dentaland.services.notifications.send_appointment_reminder",
        side_effect=fake_send,
    ):
        t1 = threading.Thread(target=worker, args=("a", factory_a))
        t2 = threading.Thread(target=worker, args=("b", factory_b))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

    assert not t1.is_alive()
    assert not t2.is_alive()
    assert len(send_calls) == 1, f"očekivano tačno jedno slanje, dobijeno: {send_calls}"
    assert results["a"] + results["b"] == 1

    verify_engine = create_engine(db_url)
    with sessionmaker(bind=verify_engine)() as session:
        stored = session.query(Appointment).filter_by(email="pacijent@example.com").one()
        assert stored.reminder_sent_at is not None
    verify_engine.dispose()


def test_scheduler_odbija_naivno_trenutno_vrijeme(
    session_factory: sessionmaker[Session],
) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        send_due_appointment_reminders(session_factory, now=datetime(2026, 8, 20, 8, 0))


def test_backend_startup_automatski_pokrece_scheduler(
    session_factory: sessionmaker[Session],
) -> None:
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    try:
        with patch(
            "backend.main.run_reminder_scheduler", new_callable=AsyncMock
        ) as scheduler, TestClient(app):
            pass
        scheduler.assert_awaited_once_with(session_factory)
    finally:
        app.dependency_overrides.clear()
