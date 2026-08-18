"""Testovi servisnog sloja za štampu rasporeda (DENT-015)."""

from __future__ import annotations

import inspect
from dataclasses import fields
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dentaland.models import (
    Appointment,
    AppointmentStatus,
    Base,
    Doctor,
    Service,
    TimeOff,
    WorkingHours,
)
from dentaland.services import AppointmentService
from dentaland.services import print_schedule as ps
from dentaland.services.print_schedule import (
    PrintScheduleBlock,
    PrintScheduleEntry,
    build_day_schedule,
    build_week_schedule,
)

SARAJEVO = ZoneInfo("Europe/Sarajevo")

PON = date(2026, 8, 17)
UTO = date(2026, 8, 18)
SRI = date(2026, 8, 19)
SUB = date(2026, 8, 22)
NED = date(2026, 8, 23)


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
def appointment_service(session_factory: sessionmaker[Session]) -> AppointmentService:
    with session_factory() as session:
        doctor = Doctor(ime="Ljubo")
        service = Service(naziv="Kontrola", trajanje_min=30, buffer_min=0)
        session.add_all([doctor, service])
        session.flush()
        doctor_id = doctor.id
        session.commit()
    return AppointmentService(session_factory, doctor_id=doctor_id)


def _local(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SARAJEVO)


def _make_appointment(
    service: AppointmentService,
    session_factory: sessionmaker[Session],
    patient: str,
    start: datetime,
    end: datetime,
    *,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
    confirmed_at: datetime | None = None,
    arrived_at: datetime | None = None,
) -> None:
    dto = service.create(patient, "061", "x@y.com", "Kontrola", "napomena", start, end)
    with session_factory() as session:
        appt = session.get(Appointment, dto.id)
        assert appt is not None
        appt.status = status
        appt.confirmed_at = confirmed_at
        appt.arrived_at = arrived_at
        session.commit()


def test_dataclassi_nemaju_privatna_polja_u_tipu() -> None:
    for cls in (PrintScheduleEntry, PrintScheduleBlock, ps.PrintSchedule):
        names = {f.name for f in fields(cls)}
        assert not names & {"phone", "email", "note", "telefon", "napomena"}


def test_nema_qt_importa() -> None:
    source = inspect.getsource(ps)
    assert "PySide6" not in source
    assert "PyQt" not in source


def test_build_day_schedule_ukljucuje_dozvoljena_polja(
    appointment_service: AppointmentService,
    session_factory: sessionmaker[Session],
) -> None:
    _make_appointment(
        appointment_service, session_factory, "Ana", _local(UTO, 9), _local(UTO, 9, 30)
    )
    result = build_day_schedule(appointment_service, UTO)

    assert result.title == "Utorak, 18.08.2026."
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.time_range == "09:00–09:30"
    assert entry.patient_name == "Ana"
    assert entry.doctor_name == "Ljubo"
    assert entry.service == "Kontrola"
    assert entry.status_label == "Čeka potvrdu"


def test_build_day_schedule_iskljucuje_cancelled_noshow_i_van_dana(
    appointment_service: AppointmentService,
    session_factory: sessionmaker[Session],
) -> None:
    _make_appointment(
        appointment_service, session_factory, "Ana", _local(UTO, 9), _local(UTO, 9, 30)
    )
    _make_appointment(
        appointment_service,
        session_factory,
        "Marko",
        _local(UTO, 10),
        _local(UTO, 10, 30),
        status=AppointmentStatus.CANCELLED,
    )
    _make_appointment(
        appointment_service,
        session_factory,
        "Petar",
        _local(UTO, 11),
        _local(UTO, 11, 30),
        status=AppointmentStatus.NO_SHOW,
    )
    _make_appointment(
        appointment_service, session_factory, "Jelena", _local(SRI, 9), _local(SRI, 9, 30)
    )

    result = build_day_schedule(appointment_service, UTO)
    assert [e.patient_name for e in result.entries] == ["Ana"]


def test_build_week_schedule_pokriva_pon_sub_ne_nedelju(
    appointment_service: AppointmentService,
    session_factory: sessionmaker[Session],
) -> None:
    _make_appointment(
        appointment_service, session_factory, "Pon", _local(PON, 9), _local(PON, 9, 30)
    )
    _make_appointment(
        appointment_service, session_factory, "Sub", _local(SUB, 9), _local(SUB, 9, 30)
    )
    _make_appointment(
        appointment_service, session_factory, "Ned", _local(NED, 9), _local(NED, 9, 30)
    )

    result = build_week_schedule(appointment_service, PON)
    assert {e.patient_name for e in result.entries} == {"Pon", "Sub"}
    assert result.title == "17.08. – 22.08.2026."

    by_name = {e.patient_name: e.day_label for e in result.entries}
    assert by_name["Pon"] == "Pon"
    assert by_name["Sub"] == "Sub"


def test_day_label_je_isti_dan_za_sve_entries_u_build_day_schedule(
    appointment_service: AppointmentService,
    session_factory: sessionmaker[Session],
) -> None:
    _make_appointment(
        appointment_service, session_factory, "Prvi", _local(SRI, 9), _local(SRI, 9, 30)
    )
    _make_appointment(
        appointment_service, session_factory, "Drugi", _local(SRI, 11), _local(SRI, 11, 30)
    )

    result = build_day_schedule(appointment_service, SRI)
    assert all(e.day_label == "Sri" for e in result.entries)


def test_status_label_poklapa_se_sa_legendom(
    appointment_service: AppointmentService,
    session_factory: sessionmaker[Session],
) -> None:
    _make_appointment(
        appointment_service, session_factory, "Ceka", _local(UTO, 9), _local(UTO, 9, 30)
    )
    _make_appointment(
        appointment_service,
        session_factory,
        "Potvrdjen",
        _local(UTO, 10),
        _local(UTO, 10, 30),
        confirmed_at=_local(UTO, 8),
    )
    _make_appointment(
        appointment_service,
        session_factory,
        "Stigao",
        _local(UTO, 11),
        _local(UTO, 11, 30),
        arrived_at=_local(UTO, 11),
    )
    _make_appointment(
        appointment_service,
        session_factory,
        "Zavrsen",
        _local(UTO, 12),
        _local(UTO, 12, 30),
        status=AppointmentStatus.COMPLETED,
    )

    result = build_day_schedule(appointment_service, UTO)
    labels = {e.patient_name: e.status_label for e in result.entries}
    assert labels == {
        "Ceka": "Čeka potvrdu",
        "Potvrdjen": "Potvrđen",
        "Stigao": "Stigao",
        "Zavrsen": "Završen",
    }


def test_entries_sortirani_hronoloski(
    appointment_service: AppointmentService,
    session_factory: sessionmaker[Session],
) -> None:
    _make_appointment(
        appointment_service, session_factory, "Kasniji", _local(UTO, 11), _local(UTO, 11, 30)
    )
    _make_appointment(
        appointment_service, session_factory, "Raniji", _local(UTO, 9), _local(UTO, 9, 30)
    )
    _make_appointment(
        appointment_service, session_factory, "Srednji", _local(UTO, 10), _local(UTO, 10, 30)
    )

    result = build_day_schedule(appointment_service, UTO)
    assert [e.patient_name for e in result.entries] == ["Raniji", "Srednji", "Kasniji"]


def test_blokovi_odsustvo_i_pauza_u_danu_i_sedmici(
    appointment_service: AppointmentService,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        session.add(
            TimeOff(
                doctor_id=appointment_service.doctor_id,
                od_datetime=_local(UTO, 10),
                do_datetime=_local(UTO, 11),
                razlog="VAN ORDINACIJE",
            )
        )
        session.add_all(
            [
                WorkingHours(
                    doctor_id=appointment_service.doctor_id,
                    dan_u_sedmici=2,
                    od_local=time(8, 0),
                    do_local=time(12, 0),
                    timezone="Europe/Sarajevo",
                ),
                WorkingHours(
                    doctor_id=appointment_service.doctor_id,
                    dan_u_sedmici=2,
                    od_local=time(13, 0),
                    do_local=time(18, 0),
                    timezone="Europe/Sarajevo",
                ),
            ]
        )
        session.commit()

    day_result = build_day_schedule(appointment_service, UTO)
    assert {b.label for b in day_result.blocks} == {"Van ordinacije", "Pauza"}
    assert all(b.doctor_name == "Ljubo" for b in day_result.blocks)
    assert all(b.day_label == "Uto" for b in day_result.blocks)
    day_ranges = sorted(b.time_range for b in day_result.blocks)
    assert day_ranges == ["10:00–11:00", "12:00–13:00"]

    week_result = build_week_schedule(appointment_service, PON)
    assert {b.label for b in week_result.blocks} == {"Van ordinacije", "Pauza"}
    assert all(b.day_label == "Uto" for b in week_result.blocks)
