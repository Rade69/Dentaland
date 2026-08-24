"""Appointment CRUD/status/DTO servis (REF-03).

Vlasnik svega što se tiče pojedinačnog termina: CRUD, status tranzicije,
range reads i service lookup potreban appointment editoru. Izdvojeno iz
``booking.py`` (koji je sada tanak facade) — logika identična, samo
premještena.

Overlap provjera je dijeljena kroz
``availability.validate_appointment_overlap`` (REF-01) — nema dupliranog
overlap SQL-a.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from dentaland.models import Appointment, AppointmentStatus, Doctor, Service, utcnow
from dentaland.services.availability import validate_appointment_overlap


@dataclass
class AppointmentDTO:
    """Termin u obliku koji GUI očekuje (plain podaci, ne SQLAlchemy objekat).

    ``doctor_id``/``doctor_name`` omogućavaju boja-kodiranje po doktoru u
    kombinovanom sedmičnom prikazu (DENT-006).
    """

    id: int
    patient_name: str
    phone: str
    email: str
    service: str
    note: str
    start: datetime
    end: datetime
    doctor_id: int
    doctor_name: str
    status: AppointmentStatus
    confirmed_at: datetime | None
    arrived_at: datetime | None


@dataclass
class ServiceOptionDTO:
    """Stabilan read-model usluge za GUI (id, naziv, trajanje, buffer).

    Trajanje dolazi iz ``Service.trajanje_min`` — nikad se ne izmišlja ni
    hardkoduje na strani GUI-ja (Faza A redizajna).
    """

    id: int
    naziv: str
    trajanje_min: int
    buffer_min: int


def create_appointment(
    session_factory: Callable[[], Session],
    doctor_id: int,
    patient_name: str,
    phone: str,
    email: str,
    service: str,
    note: str,
    start: datetime,
    end: datetime,
) -> AppointmentDTO:
    with session_factory() as session:
        validate_appointment_overlap(session, doctor_id, start, end)
        service_obj = _get_service(session, service)
        appt = Appointment(
            doctor_id=doctor_id,
            service_id=service_obj.id,
            ime=patient_name,
            telefon=phone,
            email=email,
            napomena=note,
            start_time=start,
            end_time=end,
            status=AppointmentStatus.SCHEDULED,
        )
        session.add(appt)
        session.commit()
        return _to_dto(appt, service_obj.naziv)


def update_appointment(
    session_factory: Callable[[], Session],
    appt_id: int,
    *,
    patient_name: str,
    phone: str,
    email: str,
    doctor_id: int,
    service: str,
    note: str,
    start: datetime,
    end: datetime,
) -> AppointmentDTO:
    """Uredi postojeći termin — sva polja, sa overlap provjerom za novog doktora.

    Dozvoljeno samo za ``SCHEDULED`` termin (terminalna stanja su
    read-only). ``exclude_id=appt_id`` osigurava da termin pri editovanju
    ne vidi sam sebe kao preklapanje (isti obrazac kao ``move_appointment``).
    """
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        if appt.status != AppointmentStatus.SCHEDULED:
            raise ValueError("samo zakazan termin može biti uređen")
        doctor = session.get(Doctor, doctor_id)
        if doctor is None:
            raise ValueError(f"nepoznat doktor: {doctor_id}")
        service_obj = _get_service(session, service)
        validate_appointment_overlap(session, doctor_id, start, end, exclude_id=appt_id)
        appt.ime = patient_name
        appt.telefon = phone
        appt.email = email
        appt.doctor_id = doctor_id
        appt.service_id = service_obj.id
        appt.napomena = note
        appt.start_time = start
        appt.end_time = end
        session.commit()
        return _to_dto(appt, service_obj.naziv)


def get_appointment(session_factory: Callable[[], Session], appt_id: int) -> AppointmentDTO | None:
    with session_factory() as session:
        appt = session.scalar(select(Appointment).where(Appointment.id == appt_id))
        if appt is None:
            return None
        return _to_dto(appt, _service_name(appt))


def list_appointments(
    session_factory: Callable[[], Session], doctor_id: int
) -> list[AppointmentDTO]:
    with session_factory() as session:
        appts = session.scalars(
            select(Appointment)
            .where(Appointment.doctor_id == doctor_id)
            .order_by(Appointment.start_time)
        ).all()
        return [_to_dto(a, _service_name(a)) for a in appts]


def all_combined_appointments(session_factory: Callable[[], Session]) -> list[AppointmentDTO]:
    """Termini svih doktora odjednom (za kombinovani sedmični prikaz).

    Mora ostati identična ranijem ``AppointmentService.all_combined()`` —
    koristi je ``print_schedule.py`` (van scope-a). Namjerno BEZ eager load
    (isti lazy obrazac kao prije REF-02).
    """
    with session_factory() as session:
        appts = session.scalars(
            select(Appointment)
            .where(
                Appointment.start_time.is_not(None),
                Appointment.end_time.is_not(None),
                Appointment.doctor_id.is_not(None),
                Appointment.service_id.is_not(None),
                Appointment.status.not_in(
                    [AppointmentStatus.PENDING, AppointmentStatus.REJECTED]
                ),
            )
            .order_by(Appointment.start_time)
        ).all()
        return [_to_dto(a, _service_name(a)) for a in appts]


def appointments_for_range(
    session_factory: Callable[[], Session],
    range_start: datetime,
    range_end: datetime,
    doctor_id: int | None = None,
) -> list[AppointmentDTO]:
    """Termini koji se vremenski preklapaju sa ``[range_start, range_end)``.

    Intervalska overlap semantika (isto kao ``validate_appointment_overlap``
    iz ``availability.py``): ``start_time < range_end AND end_time >
    range_start``. Doctor i Service se učitavaju ``selectinload``-om (bez
    N+1). ``doctor_id=None`` vraća sve doktore.
    """
    with session_factory() as session:
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.doctor),
                selectinload(Appointment.service),
            )
            .where(
                Appointment.start_time.is_not(None),
                Appointment.end_time.is_not(None),
                Appointment.doctor_id.is_not(None),
                Appointment.service_id.is_not(None),
                Appointment.status.not_in(
                    [AppointmentStatus.PENDING, AppointmentStatus.REJECTED]
                ),
                Appointment.start_time < range_end,
                Appointment.end_time > range_start,
            )
            .order_by(Appointment.start_time)
        )
        if doctor_id is not None:
            stmt = stmt.where(Appointment.doctor_id == doctor_id)
        appts = session.scalars(stmt).all()
        return [_to_dto(a, _service_name(a)) for a in appts]


def mark_arrived(session_factory: Callable[[], Session], appt_id: int) -> AppointmentDTO:
    """Označi da je pacijent stigao; dozvoljeno samo za zakazan termin."""
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        if appt.status != AppointmentStatus.SCHEDULED:
            raise ValueError("samo zakazan termin može biti označen kao stigao")
        appt.arrived_at = utcnow()
        session.commit()
        return _to_dto(appt, _service_name(appt))


def unmark_arrived(session_factory: Callable[[], Session], appt_id: int) -> AppointmentDTO:
    """Poništi "stigao" (npr. slučajan klik) — vrati termin na prethodni status."""
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        appt.arrived_at = None
        session.commit()
        return _to_dto(appt, _service_name(appt))


def mark_confirmed(session_factory: Callable[[], Session], appt_id: int) -> AppointmentDTO:
    """Označi ručno unesen termin kao potvrđen (npr. nakon poziva pacijentu).

    Odvojeno od ``confirm_request`` (DENT-007) — ovo je za termine koje je
    osoblje unijelo direktno u kalendar (bez web zahtjeva), pa ``confirmed_at``
    nikad nije postavljen pri kreiranju (vidi ``create_appointment``).
    """
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        if appt.status != AppointmentStatus.SCHEDULED:
            raise ValueError("samo zakazan termin može biti označen kao potvrđen")
        appt.confirmed_at = utcnow()
        session.commit()
        return _to_dto(appt, _service_name(appt))


def cancel_appointment(session_factory: Callable[[], Session], appt_id: int) -> AppointmentDTO:
    """Otkaži zakazan termin (npr. pacijent odustao ili greška pri unosu)."""
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        if appt.status != AppointmentStatus.SCHEDULED:
            raise ValueError("samo zakazan termin može biti otkazan")
        appt.status = AppointmentStatus.CANCELLED
        session.commit()
        return _to_dto(appt, _service_name(appt))


def delete_appointment(session_factory: Callable[[], Session], appt_id: int) -> None:
    """Trajno ukloni termin — isključivo za greškom kreiran zapis.

    Za razliku od ``cancel_appointment`` (zapis ostaje u istoriji), ovo je
    nepovratan hard delete. Dozvoljeno za bilo koji status (greška u unosu
    se može otkriti i nakon što je termin već označen završenim/otkazanim).

    FK provjera (DENT-DESKTOP-F plan): ništa u trenutnoj šemi ne referencira
    ``appointments.id`` kao strani ključ (Appointment ima FK-ove KA
    Doctor/Service, ne obrnuto), pa je prost DELETE bez cascade rizika.
    """
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        session.delete(appt)
        session.commit()


def mark_completed(session_factory: Callable[[], Session], appt_id: int) -> AppointmentDTO:
    """Označi termin kao završen; dozvoljeno samo za zakazan termin."""
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        if appt.status != AppointmentStatus.SCHEDULED:
            raise ValueError("samo zakazan termin može biti označen kao završen")
        appt.status = AppointmentStatus.COMPLETED
        session.commit()
        return _to_dto(appt, _service_name(appt))


def mark_no_show(session_factory: Callable[[], Session], appt_id: int) -> AppointmentDTO:
    """Označi termin kao 'nije došao'; dozvoljeno samo za zakazan termin."""
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        if appt.status != AppointmentStatus.SCHEDULED:
            raise ValueError("samo zakazan termin može biti označen kao 'nije došao'")
        appt.status = AppointmentStatus.NO_SHOW
        session.commit()
        return _to_dto(appt, _service_name(appt))


def awaiting_confirmation(session_factory: Callable[[], Session]) -> list[AppointmentDTO]:
    with session_factory() as session:
        rows = session.scalars(
            select(Appointment)
            .where(
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.confirmed_at.is_(None),
                Appointment.start_time.is_not(None),
            )
            .order_by(Appointment.start_time)
        ).all()
        return [_to_dto(row, _service_name(row)) for row in rows]


def cancelled_today(
    session_factory: Callable[[], Session], day: date | None = None
) -> list[AppointmentDTO]:
    zone = ZoneInfo("Europe/Sarajevo")
    day = day or datetime.now(zone).date()
    start = datetime.combine(day, time.min, tzinfo=zone)
    end = start + timedelta(days=1)
    with session_factory() as session:
        rows = session.scalars(
            select(Appointment)
            .where(
                Appointment.status.in_(
                    [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]
                ),
                Appointment.start_time >= start,
                Appointment.start_time < end,
            )
            .order_by(Appointment.start_time)
        ).all()
        return [_to_dto(row, _service_name(row)) for row in rows]


def move_appointment(
    session_factory: Callable[[], Session],
    appt_id: int,
    new_start: datetime,
    new_end: datetime,
) -> AppointmentDTO:
    with session_factory() as session:
        appt = session.scalar(select(Appointment).where(Appointment.id == appt_id))
        if appt is None:
            raise ValueError(f"termin {appt_id} nije pronađen")
        assert appt.doctor_id is not None, "move() radi samo nad već dodijeljenim terminima"
        # Overlap se provjerava za doktora SAMOG termina, ne za self.doctor_id
        # — drag&drop mora raditi i u kombinovanom prikazu (DENT-006).
        validate_appointment_overlap(
            session, appt.doctor_id, new_start, new_end, exclude_id=appt_id
        )
        appt.start_time = new_start
        appt.end_time = new_end
        session.commit()
        return _to_dto(appt, _service_name(appt))


def list_service_names(session_factory: Callable[[], Session]) -> list[str]:
    with session_factory() as session:
        services = session.scalars(select(Service).order_by(Service.naziv)).all()
        return [s.naziv for s in services]


def service_choices(session_factory: Callable[[], Session]) -> list[tuple[int, str]]:
    with session_factory() as session:
        rows = session.scalars(select(Service).order_by(Service.naziv)).all()
        return [(row.id, row.naziv) for row in rows]


def service_options(session_factory: Callable[[], Session]) -> list[ServiceOptionDTO]:
    """Usluge sa trajanjem i bufferom (za GUI editor — trajanje se ne izmišlja)."""
    with session_factory() as session:
        rows = session.scalars(select(Service).order_by(Service.naziv)).all()
        return [
            ServiceOptionDTO(
                id=row.id,
                naziv=row.naziv,
                trajanje_min=row.trajanje_min,
                buffer_min=row.buffer_min,
            )
            for row in rows
        ]


def _get_service(session: Session, service_name: str) -> Service:
    service = session.scalar(select(Service).where(Service.naziv == service_name))
    if service is None:
        raise ValueError(f"nepoznata usluga: {service_name}")
    return service


def _service_name(appt: Appointment) -> str:
    assert appt.service is not None, "termin bez usluge nije nadležnost appointments.py"
    return appt.service.naziv


def _to_dto(appt: Appointment, service_name: str) -> AppointmentDTO:
    assert appt.start_time is not None
    assert appt.end_time is not None
    assert appt.doctor_id is not None
    assert appt.doctor is not None
    return AppointmentDTO(
        id=appt.id,
        patient_name=appt.ime,
        phone=appt.telefon or "",
        email=appt.email or "",
        service=service_name,
        note=appt.napomena or "",
        start=appt.start_time,
        end=appt.end_time,
        doctor_id=appt.doctor_id,
        doctor_name=appt.doctor.ime,
        status=appt.status,
        confirmed_at=appt.confirmed_at,
        arrived_at=appt.arrived_at,
    )
