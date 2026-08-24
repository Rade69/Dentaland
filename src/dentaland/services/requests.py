"""Servisni sloj za javne zahtjeve sa web forme (DENT-007).

Zahtjev stiže bez doktora/usluge/tačnog vremena (bira ih pacijent na
javnoj formi samo po datumu — vidi ``docs/dentaland-javna-forma-spec.md``).
Osoblje ga potvrđuje (bira doktora/uslugu/vrijeme) ili odbija.

Provjera preklapanja je (od REF-01) dijeljena kroz
``availability.validate_appointment_overlap`` — nema više duplikata
overlap SQL-a (raniji razlog za duplikaciju bio je paralelni rad DENT-006/007,
koji više nije aktivan).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from dentaland.models import Appointment, AppointmentStatus, Service, utcnow
from dentaland.services.availability import (
    OverlapError,  # noqa: F401 — re-eksport kanonične klase (backward-compat)
    validate_appointment_overlap,
)
from dentaland.services.notifications import send_appointment_confirmed


class RequestNotFoundError(Exception):
    """Zahtjev ne postoji ili nije u PENDING statusu."""


@dataclass
class RequestDTO:
    """Javni zahtjev u obliku koji osoblje vidi (plain podaci)."""

    id: int
    ime: str
    telefon: str
    email: str
    requested_date: date
    created_at: datetime


def create_request(
    session_factory: Callable[[], Session],
    ime: str,
    telefon: str,
    email: str,
    requested_date: date,
) -> RequestDTO:
    """Upiši javni zahtjev kao PENDING — bez doktora/usluge/tačnog vremena."""
    with session_factory() as session:
        appt = Appointment(
            ime=ime,
            telefon=telefon,
            email=email,
            requested_date=requested_date,
            status=AppointmentStatus.PENDING,
        )
        session.add(appt)
        session.commit()
        return _to_dto(appt)


def list_pending(session_factory: Callable[[], Session]) -> list[RequestDTO]:
    with session_factory() as session:
        rows = session.scalars(
            select(Appointment)
            .where(Appointment.status == AppointmentStatus.PENDING)
            .order_by(Appointment.created_at)
        ).all()
        return [_to_dto(a) for a in rows]


def confirm_request(
    session_factory: Callable[[], Session],
    request_id: int,
    doctor_id: int,
    service_id: int,
    start_time: datetime,
) -> None:
    """Potvrdi zahtjev — dodijeli doktora/uslugu/vrijeme, provjeri preklapanje."""
    with session_factory() as session:
        appt = session.scalar(
            select(Appointment).where(
                Appointment.id == request_id,
                Appointment.status == AppointmentStatus.PENDING,
            )
        )
        if appt is None:
            raise RequestNotFoundError(f"zahtjev {request_id} nije pronađen ili nije PENDING")

        service = session.get(Service, service_id)
        if service is None:
            raise ValueError(f"nepoznata usluga: {service_id}")
        end_time = start_time + timedelta(minutes=service.trajanje_min)

        validate_appointment_overlap(session, doctor_id, start_time, end_time)

        appt.doctor_id = doctor_id
        appt.service_id = service_id
        appt.start_time = start_time
        appt.end_time = end_time
        appt.status = AppointmentStatus.SCHEDULED
        appt.confirmed_at = utcnow()
        patient_email = appt.email
        session.commit()

    # Best-effort, van session konteksta (SMTP ishod ne zavisi od baze) —
    # radi bez obzira ko poziva confirm_request (backend API ili desktop
    # dashboard), jer je ožičeno ovdje, ne na pojedinačnom pozivnom mjestu.
    send_appointment_confirmed(patient_email or "", start_time)


def reject_request(session_factory: Callable[[], Session], request_id: int) -> None:
    with session_factory() as session:
        appt = session.scalar(
            select(Appointment).where(
                Appointment.id == request_id,
                Appointment.status == AppointmentStatus.PENDING,
            )
        )
        if appt is None:
            raise RequestNotFoundError(f"zahtjev {request_id} nije pronađen ili nije PENDING")
        appt.status = AppointmentStatus.REJECTED
        session.commit()


def _to_dto(appt: Appointment) -> RequestDTO:
    assert appt.requested_date is not None
    return RequestDTO(
        id=appt.id,
        ime=appt.ime,
        telefon=appt.telefon or "",
        email=appt.email or "",
        requested_date=appt.requested_date,
        created_at=appt.created_at,
    )
