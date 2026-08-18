"""Testovi FastAPI backend-a za javne zahtjeve (DENT-007)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app, get_session_factory
from dentaland.models import Base, Doctor, Service


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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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


def test_get_pending_lista_podnesene_zahtjeve(client: TestClient) -> None:
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
    client: TestClient, doctor_and_service: tuple[int, int]
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
    client: TestClient, session_factory: sessionmaker[Session], doctor_and_service: tuple[int, int]
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
    client: TestClient, doctor_and_service: tuple[int, int]
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


def test_reject_uspjesno_vraca_204(client: TestClient) -> None:
    submit = client.post(
        "/api/booking-requests",
        json={"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"},
    )
    request_id = submit.json()["id"]

    response = client.post(f"/api/booking-requests/{request_id}/reject")
    assert response.status_code == 204
    assert client.get("/api/booking-requests").json() == []


def test_reject_nepostojeceg_vraca_404(client: TestClient) -> None:
    response = client.post("/api/booking-requests/999/reject")
    assert response.status_code == 404


def test_rate_limit_na_submit_endpointu(client: TestClient) -> None:
    payload = {"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"}
    statuses = [client.post("/api/booking-requests", json=payload).status_code for _ in range(11)]
    assert 429 in statuses, "11. zahtjev u minuti treba da bude odbijen (limit 10/minute)"
