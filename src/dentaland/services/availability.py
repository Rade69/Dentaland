"""Jedan source of truth za dostupnost (availability) — overlap invariant.

REF-01: ukida dupliranu overlap logiku iz ``booking.py`` i ``requests.py``
(duplikacija je bila taktička odluka iz DENT-007 radi paralelnog rada; taj
razlog više ne postoji).

Kanonična ``OverlapError`` klasa živi ovdje. ``booking.py`` i ``requests.py``
je re-eksportuju radi backward-compat import putanja (postojeći kod koji
radi ``from dentaland.services.booking import OverlapError`` ili
``from dentaland.services.requests import OverlapError`` i dalje dobija istu,
kanoničnu klasu).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from dentaland.models import Appointment, AppointmentStatus


class OverlapError(Exception):
    """Dva aktivna termina istog doktora se vremenski preklapaju."""


def validate_appointment_overlap(
    session: Session,
    doctor_id: int,
    start: datetime,
    end: datetime,
    exclude_id: int | None = None,
) -> None:
    """Podigni ``OverlapError`` ako postoji aktivan termin istog doktora
    koji se preklapa sa intervalom ``[start, end)``.

    Blokiraju se SAMO statusi koji predstavljaju aktivnu rezervaciju
    (``SCHEDULED``) — konzistentno sa budućim EXCLUDE constraint pravilom iz
    ``docs/dentaland-razvojni-plan-v3.1.md``. ``exclude_id`` isključuje sam
    termin pri pomjeranju, da termin ne "preklapa" samog sebe.
    """
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status == AppointmentStatus.SCHEDULED,
        Appointment.start_time < end,
        Appointment.end_time > start,
    )
    if exclude_id is not None:
        stmt = stmt.where(Appointment.id != exclude_id)
    if session.scalar(stmt) is not None:
        raise OverlapError(
            "termin se preklapa sa postojećim aktivnim terminom istog doktora"
        )
