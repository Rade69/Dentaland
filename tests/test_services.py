"""Testovi servisnog sloja za termine (DENT-003)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dentaland.models import Appointment, AppointmentStatus, Base, Doctor, Service
from dentaland.services import AppointmentService, OverlapError, ensure_seed_data


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


def _make_service(session: Session, naziv: str = "Kontrola") -> None:
    session.add(Service(naziv=naziv, trajanje_min=30, buffer_min=0))
    session.flush()


@pytest.fixture()
def appointment_service(session_factory: sessionmaker[Session]) -> AppointmentService:
    with session_factory() as session:
        doctor_id = _make_doctor(session)
        _make_service(session)
        session.commit()
    return AppointmentService(session_factory, doctor_id=doctor_id)


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 17, hour, minute, tzinfo=UTC)


def test_create_bez_konflikta(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create(
        "Ana Anić", "061", "ana@x.com", "Kontrola", "", _at(9), _at(9, 30)
    )

    assert dto.patient_name == "Ana Anić"
    assert dto.service == "Kontrola"
    assert dto.start == _at(9)
    assert [a.id for a in appointment_service.all()] == [dto.id]


def test_create_odbija_preklapanje(appointment_service: AppointmentService) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))

    with pytest.raises(OverlapError):
        appointment_service.create("Marko", "", "", "Kontrola", "", _at(9, 15), _at(9, 45))


def test_create_dozvoljava_drugog_doktora(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))

    with session_factory() as session:
        other_id = _make_doctor(session, "Zorka")
        session.commit()
    other_service = AppointmentService(session_factory, doctor_id=other_id)

    dto = other_service.create("Marko", "", "", "Kontrola", "", _at(9), _at(9, 30))
    assert dto.patient_name == "Marko"


def test_move_uspjesno(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))

    moved = appointment_service.move(dto.id, _at(10), _at(10, 30))
    assert moved.start == _at(10)
    assert moved.end == _at(10, 30)


def test_move_odbija_preklapanje(appointment_service: AppointmentService) -> None:
    first = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.create("Marko", "", "", "Kontrola", "", _at(10), _at(10, 30))

    with pytest.raises(OverlapError):
        appointment_service.move(first.id, _at(10, 15), _at(10, 45))


def test_cancelled_ne_blokira_slot(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    _set_status(session_factory, AppointmentStatus.CANCELLED)

    dto = appointment_service.create("Marko", "", "", "Kontrola", "", _at(9, 15), _at(9, 45))
    assert dto.patient_name == "Marko"


def test_completed_ne_blokira_slot(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    _set_status(session_factory, AppointmentStatus.COMPLETED)

    dto = appointment_service.create("Marko", "", "", "Kontrola", "", _at(9, 15), _at(9, 45))
    assert dto.patient_name == "Marko"


def test_no_show_ne_blokira_slot(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    _set_status(session_factory, AppointmentStatus.NO_SHOW)

    dto = appointment_service.create("Marko", "", "", "Kontrola", "", _at(9, 15), _at(9, 45))
    assert dto.patient_name == "Marko"


def test_preklapanje_termina_duzeg_od_slota(appointment_service: AppointmentService) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(10))  # 60 min

    with pytest.raises(OverlapError):
        appointment_service.create("Marko", "", "", "Kontrola", "", _at(9, 30), _at(10))
    with pytest.raises(OverlapError):
        appointment_service.create("Petar", "", "", "Kontrola", "", _at(9, 30), _at(10, 30))

    # Tačno na kraju prvog termina — dozvoljeno ([) granica).
    dto = appointment_service.create("Jelena", "", "", "Kontrola", "", _at(10), _at(10, 30))
    assert dto.patient_name == "Jelena"


def test_ensure_seed_data(session_factory: sessionmaker[Session]) -> None:
    ensure_seed_data(session_factory)
    ensure_seed_data(session_factory)  # idempotentno

    with session_factory() as session:
        doctors = session.scalars(select(Doctor)).all()
        services = session.scalars(select(Service)).all()

    assert [doctor.ime for doctor in doctors] == ["Ljubo", "Zorka", "Ana"]
    assert len(services) == 5


def test_all_combined_vraca_termina_svih_doktora(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))

    with session_factory() as session:
        zorka_id = _make_doctor(session, "Zorka")
        session.commit()
    zorka_service = AppointmentService(session_factory, doctor_id=zorka_id)
    zorka_service.create("Marko", "", "", "Kontrola", "", _at(10), _at(10, 30))

    combined = appointment_service.all_combined()
    assert {d.patient_name for d in combined} == {"Ana", "Marko"}
    assert {d.doctor_name for d in combined} == {"Ljubo", "Zorka"}


def test_move_radi_za_termin_drugog_doktora(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    with session_factory() as session:
        zorka_id = _make_doctor(session, "Zorka")
        session.commit()
    zorka_service = AppointmentService(session_factory, doctor_id=zorka_id)
    dto = zorka_service.create("Marko", "", "", "Kontrola", "", _at(10), _at(10, 30))

    # appointment_service ima self.doctor_id = Ljubo, a pomjera Zorkin termin.
    moved = appointment_service.move(dto.id, _at(11), _at(11, 30))
    assert moved.start == _at(11)
    assert moved.doctor_name == "Zorka"


def _set_status(session_factory: sessionmaker[Session], status: AppointmentStatus) -> None:
    with session_factory() as session:
        appt = session.scalar(select(Appointment))
        assert appt is not None
        appt.status = status
        session.commit()
