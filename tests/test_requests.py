"""Testovi servisnog sloja za javne zahtjeve (DENT-007)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dentaland.models import Appointment, AppointmentStatus, Base, Doctor, Service
from dentaland.services.requests import (
    OverlapError,
    RequestNotFoundError,
    confirm_request,
    create_request,
    list_pending,
    reject_request,
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
def doctor_id(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        doctor = Doctor(ime="Ljubo")
        session.add(doctor)
        session.commit()
        return doctor.id


@pytest.fixture()
def service_id(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        service = Service(naziv="Kontrola", trajanje_min=30, buffer_min=0)
        session.add(service)
        session.commit()
        return service.id


def test_create_request_je_pending_bez_doktora_i_vremena(
    session_factory: sessionmaker[Session],
) -> None:
    dto = create_request(
        session_factory, "Ana Anić", "061/111-222", "ana@x.com", date(2026, 8, 20)
    )
    assert dto.ime == "Ana Anić"
    assert dto.requested_date == date(2026, 8, 20)

    with session_factory() as session:
        appt = session.get(Appointment, dto.id)
        assert appt.status == AppointmentStatus.PENDING
        assert appt.doctor_id is None
        assert appt.service_id is None
        assert appt.start_time is None
        assert appt.end_time is None


def test_list_pending_vraca_samo_pending(session_factory: sessionmaker[Session]) -> None:
    create_request(session_factory, "Ana", "061", "", date(2026, 8, 20))
    create_request(session_factory, "Marko", "062", "", date(2026, 8, 21))

    pending = list_pending(session_factory)
    assert {p.ime for p in pending} == {"Ana", "Marko"}


def test_confirm_request_postavlja_doktora_uslugu_vrijeme(
    session_factory: sessionmaker[Session], doctor_id: int, service_id: int
) -> None:
    dto = create_request(session_factory, "Ana", "061", "", date(2026, 8, 20))
    start = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)

    confirm_request(session_factory, dto.id, doctor_id, service_id, start)

    with session_factory() as session:
        appt = session.get(Appointment, dto.id)
        assert appt.status == AppointmentStatus.SCHEDULED
        assert appt.doctor_id == doctor_id
        assert appt.service_id == service_id
        assert appt.start_time == start
        assert appt.end_time == datetime(2026, 8, 20, 9, 30, tzinfo=UTC)  # 30 min trajanje
        assert appt.confirmed_at is not None
        assert appt.confirmed_at.utcoffset() is not None


def test_confirm_request_odbija_preklapanje(
    session_factory: sessionmaker[Session], doctor_id: int, service_id: int
) -> None:
    with session_factory() as session:
        existing = Appointment(
            doctor_id=doctor_id,
            service_id=service_id,
            ime="Postojeci",
            start_time=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 8, 20, 9, 30, tzinfo=UTC),
            status=AppointmentStatus.SCHEDULED,
        )
        session.add(existing)
        session.commit()

    dto = create_request(session_factory, "Ana", "061", "", date(2026, 8, 20))
    with pytest.raises(OverlapError):
        confirm_request(
            session_factory, dto.id, doctor_id, service_id,
            datetime(2026, 8, 20, 9, 15, tzinfo=UTC),
        )


def test_confirm_request_nepostojeceg_zahtjeva_die(
    session_factory: sessionmaker[Session], doctor_id: int, service_id: int
) -> None:
    with pytest.raises(RequestNotFoundError):
        confirm_request(
            session_factory, 999, doctor_id, service_id, datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        )


def test_confirm_request_vec_potvrdjenog_zahtjeva_die(
    session_factory: sessionmaker[Session], doctor_id: int, service_id: int
) -> None:
    dto = create_request(session_factory, "Ana", "061", "", date(2026, 8, 20))
    confirm_request(
        session_factory, dto.id, doctor_id, service_id, datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
    )
    with pytest.raises(RequestNotFoundError):
        confirm_request(
            session_factory, dto.id, doctor_id, service_id,
            datetime(2026, 8, 20, 11, 0, tzinfo=UTC),
        )


def test_reject_request_postavlja_status(session_factory: sessionmaker[Session]) -> None:
    dto = create_request(session_factory, "Ana", "061", "", date(2026, 8, 20))
    reject_request(session_factory, dto.id)

    with session_factory() as session:
        appt = session.get(Appointment, dto.id)
        assert appt.status == AppointmentStatus.REJECTED

    assert dto.id not in {p.id for p in list_pending(session_factory)}


def test_reject_request_nepostojeceg_die(session_factory: sessionmaker[Session]) -> None:
    with pytest.raises(RequestNotFoundError):
        reject_request(session_factory, 999)


def test_rejected_ne_blokira_slot(
    session_factory: sessionmaker[Session], doctor_id: int, service_id: int
) -> None:
    dto = create_request(session_factory, "Ana", "061", "", date(2026, 8, 20))
    reject_request(session_factory, dto.id)

    # Novi zahtjev na isti datum/vrijeme mora moći da se potvrdi bez konflikta
    # sa odbijenim — REJECTED nije aktivan status.
    dto2 = create_request(session_factory, "Marko", "062", "", date(2026, 8, 20))
    confirm_request(
        session_factory, dto2.id, doctor_id, service_id,
        datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
    )
    with session_factory() as session:
        appt = session.get(Appointment, dto2.id)
        assert appt.status == AppointmentStatus.SCHEDULED


def test_migracija_dozvoljava_pending_bez_doktora(tmp_path) -> None:
    """Alembic migracija (ne samo Base.metadata) mora podržati nullable polja."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine as _create_engine
    from sqlalchemy import inspect

    database_path = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")

    engine = _create_engine(f"sqlite:///{database_path.as_posix()}")
    inspector = inspect(engine)
    columns = {c["name"]: c for c in inspector.get_columns("appointments")}
    assert columns["doctor_id"]["nullable"] is True
    assert columns["service_id"]["nullable"] is True
    assert columns["start_time"]["nullable"] is True
    assert columns["end_time"]["nullable"] is True
    assert "requested_date" in columns

    checks = inspector.get_check_constraints("appointments")
    assert any("PENDING" in (c["sqltext"] or "") for c in checks)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    dto = create_request(session_factory, "Ana", "061", "", date(2026, 8, 20))
    assert dto.ime == "Ana"

    # Downgrade vraća doctor_id/service_id/start_time/end_time na NOT NULL —
    # ne može uspjeti dok postoji PENDING red sa NULL vrijednostima u njima
    # (ispravno ponašanje, ne bug: downgrade se ionako ne pokreće dok ima
    # aktivnih PENDING zahtjeva). Obrisati test red prije nego provjerimo
    # da je čisto šematsko downgrade-ovanje ispravno.
    with session_factory() as session:
        session.execute(Appointment.__table__.delete())
        session.commit()

    command.downgrade(config, "base")
    remaining = set(inspect(_create_engine(f"sqlite:///{database_path.as_posix()}")).get_table_names())
    assert remaining <= {"alembic_version"}
    engine.dispose()
