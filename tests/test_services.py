"""Testovi servisnog sloja za termine (DENT-003)."""

from __future__ import annotations

from datetime import UTC, datetime, time

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


def _future_at(hour: int, minute: int = 0) -> datetime:
    """Daleko budući trenutak — za blokade koje moraju biti 'nadolazeće'."""
    return datetime(2027, 6, 1, hour, minute, tzinfo=UTC)


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


def test_create_time_off_kreira_blokadu(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create_time_off(
        appointment_service.doctor_id, _future_at(12), _future_at(13), "Ručak"
    )
    assert dto.reason == "Ručak"
    assert dto.start == _future_at(12)
    assert dto.end == _future_at(13)
    assert [b.id for b in appointment_service.list_time_off()] == [dto.id]


def test_create_time_off_odbija_obrnut_interval(
    appointment_service: AppointmentService,
) -> None:
    with pytest.raises(ValueError):
        appointment_service.create_time_off(
            appointment_service.doctor_id, _future_at(13), _future_at(12)
        )


def test_create_time_off_odbija_preklapanje_sa_terminom(
    appointment_service: AppointmentService,
) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    with pytest.raises(OverlapError):
        appointment_service.create_time_off(
            appointment_service.doctor_id, _at(9, 15), _at(10)
        )


def test_create_time_off_dozvoljava_drugog_doktora(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    with session_factory() as session:
        other_id = _make_doctor(session, "Zorka")
        session.commit()
    other_service = AppointmentService(session_factory, doctor_id=other_id)
    dto = other_service.create_time_off(other_id, _at(9), _at(10))
    assert dto.doctor_id == other_id


def test_list_time_off_ne_vraca_prosle(
    session_factory: sessionmaker[Session],
    appointment_service: AppointmentService,
) -> None:
    future = appointment_service.create_time_off(
        appointment_service.doctor_id, _future_at(12), _future_at(13)
    )
    with session_factory() as session:
        session.add(
            TimeOff(
                doctor_id=appointment_service.doctor_id,
                od_datetime=_at(8),
                do_datetime=_at(9),
            )
        )
        session.commit()
    assert [b.id for b in appointment_service.list_time_off()] == [future.id]


def test_delete_time_off_brise(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create_time_off(
        appointment_service.doctor_id, _future_at(12), _future_at(13)
    )
    appointment_service.delete_time_off(dto.id)
    assert appointment_service.list_time_off() == []


def test_delete_time_off_nepostojeci(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError):
        appointment_service.delete_time_off(999)


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


# ── DENT-IMPROVE-005 — postavke (doktori / usluge / radno vrijeme) ──


def test_list_doctors_vraca_sve_ukljucujuci_neaktivne(
    session_factory: sessionmaker[Session], appointment_service: AppointmentService
) -> None:
    with session_factory() as session:
        _make_doctor(session, "Zorka")
        session.commit()

    doctors = appointment_service.list_doctors()
    assert [d.ime for d in doctors] == ["Ljubo", "Zorka"]
    assert all(d.aktivan for d in doctors)


def test_set_doctor_active_ne_brise_termine(appointment_service: AppointmentService) -> None:
    dto = appointment_service.create("Ana", "", "", "Kontrola", "", _at(9), _at(9, 30))
    doctor_id = appointment_service.doctor_id
    assert doctor_id is not None

    updated = appointment_service.set_doctor_active(doctor_id, False)
    assert updated.aktivan is False

    # Termin ostaje u bazi — deaktivacija ne briše istoriju.
    assert appointment_service.get(dto.id) is not None


def test_add_service_validacija(appointment_service: AppointmentService) -> None:
    with pytest.raises(ValueError, match="naziv"):
        appointment_service.add_service("  ", 30, 0)
    with pytest.raises(ValueError, match="trajanje"):
        appointment_service.add_service("X", 0, 0)
    with pytest.raises(ValueError, match="buffer"):
        appointment_service.add_service("X", 30, -1)


def test_add_i_update_service(appointment_service: AppointmentService) -> None:
    added = appointment_service.add_service("Proteza", 90, 20)
    assert added.naziv == "Proteza"
    assert added.trajanje_min == 90

    updated = appointment_service.update_service(added.id, "Proteza (nova)", 120, 25)
    assert updated.naziv == "Proteza (nova)"
    assert updated.trajanje_min == 120
    assert updated.buffer_min == 25

    options = {o.naziv: o for o in appointment_service.service_options()}
    assert options["Proteza (nova)"].trajanje_min == 120


def test_set_working_hours_split_shift(appointment_service: AppointmentService) -> None:
    doctor_id = appointment_service.doctor_id
    assert doctor_id is not None
    appointment_service.set_working_hours(
        doctor_id, 1, [(time(8, 0), time(12, 0)), (time(14, 0), time(18, 0))]
    )
    rows = appointment_service.list_working_hours(doctor_id)
    assert [(r.od_local, r.do_local) for r in rows] == [
        (time(8, 0), time(12, 0)),
        (time(14, 0), time(18, 0)),
    ]


def test_set_working_hours_zamjenjuje_prethodne(appointment_service: AppointmentService) -> None:
    doctor_id = appointment_service.doctor_id
    assert doctor_id is not None
    appointment_service.set_working_hours(doctor_id, 1, [(time(8, 0), time(16, 0))])
    appointment_service.set_working_hours(doctor_id, 1, [(time(9, 0), time(17, 0))])

    rows = appointment_service.list_working_hours(doctor_id)
    assert [(r.od_local, r.do_local) for r in rows] == [(time(9, 0), time(17, 0))]


def test_set_working_hours_validacija(appointment_service: AppointmentService) -> None:
    doctor_id = appointment_service.doctor_id
    assert doctor_id is not None

    with pytest.raises(ValueError, match="dan"):
        appointment_service.set_working_hours(doctor_id, 0, [(time(8, 0), time(16, 0))])
    with pytest.raises(ValueError, match="poslije"):
        appointment_service.set_working_hours(doctor_id, 1, [(time(16, 0), time(8, 0))])
    with pytest.raises(ValueError, match="preklapati"):
        appointment_service.set_working_hours(
            doctor_id, 1, [(time(8, 0), time(12, 0)), (time(11, 0), time(14, 0))]
        )
