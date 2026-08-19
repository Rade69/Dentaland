"""Testovi servisnog sloja za termine (DENT-003)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event, select
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


def test_dto_sadrzi_statusna_polja(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    assert dto.status == AppointmentStatus.SCHEDULED
    assert dto.confirmed_at is None
    assert dto.arrived_at is None


def test_mark_arrived_uspjeh(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    arrived = appointment_service.mark_arrived(dto.id)
    assert arrived.arrived_at is not None


def test_mark_arrived_nepostojeci_id(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="nije pronađen"):
        appointment_service.mark_arrived(999)


def test_unmark_arrived_ponistava_slucajan_klik(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.mark_arrived(dto.id)
    reverted = appointment_service.unmark_arrived(dto.id)
    assert reverted.arrived_at is None


def test_unmark_arrived_nepostojeci_id(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="nije pronađen"):
        appointment_service.unmark_arrived(999)


def test_mark_confirmed_uspjeh(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    confirmed = appointment_service.mark_confirmed(dto.id)
    assert confirmed.confirmed_at is not None


def test_mark_confirmed_uklanja_iz_cekaju_potvrdu(
    appointment_service: AppointmentService,
) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    assert [row.id for row in appointment_service.awaiting_confirmation()] == [dto.id]
    appointment_service.mark_confirmed(dto.id)
    assert appointment_service.awaiting_confirmation() == []


def test_mark_confirmed_nepostojeci_id(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="nije pronađen"):
        appointment_service.mark_confirmed(999)


def test_cancel_postavlja_status_cancelled(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    cancelled = appointment_service.cancel(dto.id)
    assert cancelled.status == AppointmentStatus.CANCELLED


def test_cancel_uklanja_iz_cekaju_potvrdu(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.cancel(dto.id)
    assert appointment_service.awaiting_confirmation() == []


def test_cancel_nepostojeci_id(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="nije pronađen"):
        appointment_service.cancel(999)


def test_delete_uklanja_termin(
    session_factory: sessionmaker[Session], appointment_service: AppointmentService
) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.delete(dto.id)
    with session_factory() as session:
        assert session.get(Appointment, dto.id) is None


def test_delete_ne_dira_druge_termine(
    session_factory: sessionmaker[Session], appointment_service: AppointmentService
) -> None:
    first = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    second = appointment_service.create("Marko", "", "", "Kontrola", "", _at(10), _at(10, 30))

    appointment_service.delete(first.id)

    with session_factory() as session:
        assert session.get(Appointment, first.id) is None
        assert session.get(Appointment, second.id) is not None


def test_delete_radi_bez_obzira_na_status(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.cancel(dto.id)  # terminalno stanje
    appointment_service.delete(dto.id)  # ne smije baciti — delete radi za bilo koji status
    assert appointment_service.get(dto.id) is None


def test_delete_nepostojeci_id(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="nije pronađen"):
        appointment_service.delete(999)


def test_odvojeni_upiti_cekaju_i_otkazani(
    session_factory: sessionmaker[Session], appointment_service: AppointmentService
) -> None:
    waiting = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    cancelled = appointment_service.create("Marko", "", "", "Kontrola", "", _at(10), _at(10, 30))
    with session_factory() as session:
        row = session.get(Appointment, cancelled.id)
        assert row is not None
        row.status = AppointmentStatus.CANCELLED
        session.commit()
    assert [row.id for row in appointment_service.awaiting_confirmation()] == [waiting.id]
    assert [row.id for row in appointment_service.cancelled_today(_at(9).date())] == [cancelled.id]


def test_timeoff_i_split_shift_pauza(
    session_factory: sessionmaker[Session], appointment_service: AppointmentService
) -> None:
    with session_factory() as session:
        doctor = session.scalar(select(Doctor))
        assert doctor is not None
        session.add(
            TimeOff(
                doctor_id=doctor.id,
                od_datetime=_at(10),
                do_datetime=_at(11),
                razlog="VAN ORDINACIJE",
            )
        )
        session.add_all(
            [
                WorkingHours(
                    doctor_id=doctor.id,
                    dan_u_sedmici=1,
                    od_local=datetime.min.time().replace(hour=8),
                    do_local=datetime.min.time().replace(hour=12),
                    timezone="Europe/Sarajevo",
                ),
                WorkingHours(
                    doctor_id=doctor.id,
                    dan_u_sedmici=1,
                    od_local=datetime.min.time().replace(hour=13),
                    do_local=datetime.min.time().replace(hour=18),
                    timezone="Europe/Sarajevo",
                ),
            ]
        )
        session.commit()
    assert appointment_service.time_off_for_week(_at(9).date())[0].label == "VAN ORDINACIJE"
    pause = appointment_service.breaks_for_week(_at(9).date())[0]
    assert pause.label == "PAUZA"
    assert pause.start.hour == 12 and pause.end.hour == 13


def test_update_mijenja_podatke(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))

    updated = appointment_service.update(
        dto.id,
        patient_name="Ana Anić",
        phone="061",
        email="ana@x.com",
        doctor_id=appointment_service.doctor_id,
        service="Kontrola",
        note="napomena",
        start=_at(9),
        end=_at(9, 30),
    )
    assert updated.patient_name == "Ana Anić"
    assert updated.phone == "061"
    assert updated.email == "ana@x.com"
    assert updated.note == "napomena"


def test_update_mijenja_doktora(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    with session_factory() as session:
        zorka_id = _make_doctor(session, "Zorka")
        session.commit()

    updated = appointment_service.update(
        dto.id,
        patient_name="Ana",
        phone="",
        email="",
        doctor_id=zorka_id,
        service="Kontrola",
        note="",
        start=_at(9),
        end=_at(9, 30),
    )
    assert updated.doctor_id == zorka_id
    assert updated.doctor_name == "Zorka"


def test_update_mijenja_vrijeme(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))

    updated = appointment_service.update(
        dto.id,
        patient_name="Ana",
        phone="",
        email="",
        doctor_id=appointment_service.doctor_id,
        service="Kontrola",
        note="",
        start=_at(11),
        end=_at(11, 30),
    )
    assert updated.start == _at(11)
    assert updated.end == _at(11, 30)


def test_update_mijenja_uslugu(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    with session_factory() as session:
        session.add(Service(naziv="Plomba", trajanje_min=60, buffer_min=15))
        session.commit()

    updated = appointment_service.update(
        dto.id,
        patient_name="Ana",
        phone="",
        email="",
        doctor_id=appointment_service.doctor_id,
        service="Plomba",
        note="",
        start=_at(9),
        end=_at(9, 30),
    )
    assert updated.service == "Plomba"


def test_update_odbija_pravi_overlap(appointment_service: AppointmentService) -> None:
    first = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.create("Marko", "", "", "Kontrola", "", _at(10), _at(10, 30))

    with pytest.raises(OverlapError):
        appointment_service.update(
            first.id,
            patient_name="Ana",
            phone="",
            email="",
            doctor_id=appointment_service.doctor_id,
            service="Kontrola",
            note="",
            start=_at(10, 15),
            end=_at(10, 45),
        )


def test_update_ne_vidi_sam_sebe_kao_overlap(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))

    # Isto vrijeme, samo promjena imena — exclude_id=appt_id mora spriječiti lažni overlap.
    updated = appointment_service.update(
        dto.id,
        patient_name="Ana A.",
        phone="",
        email="",
        doctor_id=appointment_service.doctor_id,
        service="Kontrola",
        note="",
        start=_at(9),
        end=_at(9, 30),
    )
    assert updated.patient_name == "Ana A."


def test_update_nepostojeci_id(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="nije pronađen"):
        appointment_service.update(
            999,
            patient_name="Ana",
            phone="",
            email="",
            doctor_id=appointment_service.doctor_id,
            service="Kontrola",
            note="",
            start=_at(9),
            end=_at(9, 30),
        )


def test_update_odbija_terminalni_termin(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.cancel(dto.id)

    with pytest.raises(ValueError, match="samo zakazan"):
        appointment_service.update(
            dto.id,
            patient_name="Ana",
            phone="",
            email="",
            doctor_id=appointment_service.doctor_id,
            service="Kontrola",
            note="",
            start=_at(9),
            end=_at(9, 30),
        )


def test_mark_completed_uspjeh(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    completed = appointment_service.mark_completed(dto.id)
    assert completed.status == AppointmentStatus.COMPLETED


def test_mark_no_show_uspjeh(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    no_show = appointment_service.mark_no_show(dto.id)
    assert no_show.status == AppointmentStatus.NO_SHOW


def test_mark_completed_odbija_nevalidnu_tranziciju(
    appointment_service: AppointmentService,
) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.cancel(dto.id)
    with pytest.raises(ValueError, match="samo zakazan"):
        appointment_service.mark_completed(dto.id)


def test_mark_no_show_odbija_nevalidnu_tranziciju(
    appointment_service: AppointmentService,
) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    appointment_service.mark_completed(dto.id)
    with pytest.raises(ValueError, match="samo zakazan"):
        appointment_service.mark_no_show(dto.id)


def test_mark_completed_nepostojeci_id(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="nije pronađen"):
        appointment_service.mark_completed(999)


def test_mark_no_show_nepostojeci_id(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="nije pronađen"):
        appointment_service.mark_no_show(999)


def test_service_options_vraca_trajanje_i_buffer(
    session_factory: sessionmaker[Session], appointment_service: AppointmentService
) -> None:
    with session_factory() as session:
        session.add(Service(naziv="Plomba", trajanje_min=60, buffer_min=15))
        session.commit()

    options = {o.naziv: o for o in appointment_service.service_options()}
    assert options["Kontrola"].trajanje_min == 30
    assert options["Kontrola"].buffer_min == 0
    assert options["Plomba"].trajanje_min == 60
    assert options["Plomba"].buffer_min == 15


def _set_status(session_factory: sessionmaker[Session], status: AppointmentStatus) -> None:
    with session_factory() as session:
        appt = session.scalar(select(Appointment))
        assert appt is not None
        appt.status = status
        session.commit()
