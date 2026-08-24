"""REF-01 — availability invariant + OverlapError kanonizacija.

Dokazuje da postoji JEDAN source of truth za overlap provjeru i JEDNA
kanonična ``OverlapError`` klasa (prije REF-01 su postojale dvije istoimene
klase: ``booking.OverlapError`` i ``requests.OverlapError``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import dentaland.services as services
import dentaland.services.availability as availability
import dentaland.services.booking as booking_mod
import dentaland.services.requests as requests_mod
from dentaland.models import Appointment, AppointmentStatus, Base, Doctor, Service
from dentaland.services.availability import OverlapError, validate_appointment_overlap
from dentaland.services.booking import AppointmentService


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


def _make_doctor(session: Session, ime: str = "Ljubo") -> int:
    doctor = Doctor(ime=ime)
    session.add(doctor)
    session.flush()
    return doctor.id


def _make_service(session: Session, naziv: str = "Kontrola") -> int:
    service = Service(naziv=naziv, trajanje_min=30, buffer_min=0)
    session.add(service)
    session.flush()
    return service.id


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 24, hour, minute, tzinfo=UTC)


def test_overlap_error_je_jedna_kanonicka_klasa() -> None:
    assert availability.OverlapError is booking_mod.OverlapError
    assert availability.OverlapError is requests_mod.OverlapError
    assert availability.OverlapError is services.OverlapError


def test_validate_overlap_odbija_preklapanje(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        doctor_id = _make_doctor(session)
        session.add(
            Appointment(
                doctor_id=doctor_id,
                ime="Ana",
                status=AppointmentStatus.SCHEDULED,
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )
        session.commit()

    with session_factory() as session, pytest.raises(OverlapError):
        validate_appointment_overlap(session, doctor_id, _at(9, 15), _at(9, 45))


def test_validate_overlap_dozvoljava_nepreklapanje(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        doctor_id = _make_doctor(session)
        session.add(
            Appointment(
                doctor_id=doctor_id,
                ime="Ana",
                status=AppointmentStatus.SCHEDULED,
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )
        session.commit()

    with session_factory() as session:
        validate_appointment_overlap(session, doctor_id, _at(10), _at(10, 30))


def test_validate_overlap_exclude_id(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        doctor_id = _make_doctor(session)
        appt = Appointment(
            doctor_id=doctor_id,
            ime="Ana",
            status=Appointment.__mapper__.c.status.type.python_type.SCHEDULED,
            start_time=_at(9),
            end_time=_at(9, 30),
        )
        session.add(appt)
        session.flush()
        appt_id = appt.id
        session.commit()

    with session_factory() as session:
        # Isti raspon, ali isključujući sam termin — ne smije baciti.
        validate_appointment_overlap(session, doctor_id, _at(9), _at(9, 30), exclude_id=appt_id)


def test_create_baca_kanonicku_overlap_error(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        doctor_id = _make_doctor(session)
        _make_service(session)
        session.commit()

    service = AppointmentService(session_factory, doctor_id=doctor_id)
    service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))

    with pytest.raises(OverlapError):
        service.create("Marko", "", "", "Kontrola", "", _at(9, 15), _at(9, 45))
