"""Jedan source of truth za dostupnost (availability) — overlap invariant.

REF-01: ukida dupliranu overlap logiku iz ``booking.py`` i ``requests.py``
(duplikacija je bila taktička odluka iz DENT-007 radi paralelnog rada; taj
razlog više ne postoji).

REF-03: proširuje modul na čitanje/pisanje TimeOff (blokada/odsustvo) i
generisanje kalendarskih blokova (odsustva + split-shift pauze). Overlap
invariant (``validate_appointment_overlap``/``OverlapError``) je netaknut.

Kanonična ``OverlapError`` klasa živi ovdje. ``booking.py`` i ``requests.py``
je re-eksportuju radi backward-compat import putanja (postojeći kod koji
radi ``from dentaland.services.booking import OverlapError`` ili
``from dentaland.services.requests import OverlapError`` i dalje dobija istu,
kanoničnu klasu).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from dentaland.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    TimeOff,
    WorkingHours,
    utcnow,
)
from dentaland.timezone import SARAJEVO


class OverlapError(Exception):
    """Dva aktivna termina istog doktora se vremenski preklapaju."""


@dataclass
class CalendarBlockDTO:
    """Neklikabilan raspon u kalendaru (odsustvo ili split-shift pauza)."""

    start: datetime
    end: datetime
    doctor_id: int
    label: str


@dataclass
class TimeOffDTO:
    """Blokada/odsustvo doktora u obliku koji GUI očekuje."""

    id: int
    doctor_id: int
    doctor_name: str
    start: datetime
    end: datetime
    reason: str


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


def time_off_for_week(
    session_factory: Callable[[], Session], week_start: date
) -> list[CalendarBlockDTO]:
    zone = SARAJEVO
    start = datetime.combine(week_start, time.min, tzinfo=zone)
    end = start + timedelta(days=7)
    with session_factory() as session:
        rows = session.scalars(
            select(TimeOff)
            .where(TimeOff.od_datetime < end, TimeOff.do_datetime > start)
            .order_by(TimeOff.od_datetime)
        ).all()
        return [
            CalendarBlockDTO(
                start=max(row.od_datetime, start),
                end=min(row.do_datetime, end),
                doctor_id=row.doctor_id,
                label=row.razlog or "VAN ORDINACIJE",
            )
            for row in rows
        ]


def breaks_for_week(
    session_factory: Callable[[], Session], week_start: date
) -> list[CalendarBlockDTO]:
    """``WorkingHours`` se dovlači u JEDNOM ``IN (...)`` upitu za sve aktivne
    doktore — otkriveno testiranjem preko stvarne mreže (VPS preko SSH
    tunela, 31.8.2026): stara verzija je pravila poseban upit PO doktoru
    (N doktora = N+1 upita ukupno), nezamjetno lokalno (SQLite, sub-ms
    razlika), ali stvarno mjerljivo sporo preko mreže — ova funkcija se
    zove na SVAKI refresh rasporeda (doktor tab, dan/sedmica, auto-refresh
    tajmer). Isti obrazac kao ranija N+1 popravka u
    ``appointments.awaiting_confirmation``/``cancelled_today``."""
    zone = SARAJEVO
    blocks: list[CalendarBlockDTO] = []
    with session_factory() as session:
        active_doctor_ids = [
            d.id
            for d in session.scalars(
                select(Doctor).where(Doctor.aktivan.is_(True)).order_by(Doctor.id)
            ).all()
        ]
        if not active_doctor_ids:
            return blocks
        all_rows = session.scalars(
            select(WorkingHours)
            .where(WorkingHours.doctor_id.in_(active_doctor_ids))
            .order_by(
                WorkingHours.doctor_id, WorkingHours.dan_u_sedmici, WorkingHours.od_local
            )
        ).all()
        rows_by_doctor: dict[int, list[WorkingHours]] = {}
        for row in all_rows:
            rows_by_doctor.setdefault(row.doctor_id, []).append(row)
        for doctor_id in active_doctor_ids:
            by_day: dict[int, list[WorkingHours]] = {}
            for row in rows_by_doctor.get(doctor_id, []):
                by_day.setdefault(row.dan_u_sedmici, []).append(row)
            for iso_day, periods in by_day.items():
                day = week_start + timedelta(days=iso_day - 1)
                for left, right in zip(periods, periods[1:], strict=False):
                    if left.do_local >= right.od_local:
                        continue
                    blocks.append(
                        CalendarBlockDTO(
                            start=datetime.combine(day, left.do_local, tzinfo=zone),
                            end=datetime.combine(day, right.od_local, tzinfo=zone),
                            doctor_id=doctor_id,
                            label="PAUZA",
                        )
                    )
    return blocks


def create_time_off(
    session_factory: Callable[[], Session],
    doctor_id: int,
    start: datetime,
    end: datetime,
    reason: str | None = None,
) -> TimeOffDTO:
    """Kreiraj blokadu/odsustvo za doktora.

    Odbija ``end <= start`` i preklapanje sa postojećim ``SCHEDULED``
    terminom istog doktora — postojeći termini se nikad ne obrišu ni
    pomjere, korisnik dobija eksplicitnu grešku.
    """
    if end <= start:
        raise ValueError("kraj blokade mora biti poslije početka")
    with session_factory() as session:
        doctor = session.get(Doctor, doctor_id)
        if doctor is None:
            raise ValueError(f"nepoznat doktor: {doctor_id}")
        _check_timeoff_overlap(session, doctor_id, start, end)
        block = TimeOff(
            doctor_id=doctor_id,
            od_datetime=start,
            do_datetime=end,
            razlog=reason,
        )
        session.add(block)
        session.commit()
        return TimeOffDTO(
            id=block.id,
            doctor_id=doctor_id,
            doctor_name=doctor.ime,
            start=start,
            end=end,
            reason=reason or "",
        )


def list_time_off(session_factory: Callable[[], Session]) -> list[TimeOffDTO]:
    """Aktivne i nadolazeće blokade (``do_datetime >= sada``), hronološki."""
    now = utcnow()
    with session_factory() as session:
        rows = session.scalars(
            select(TimeOff)
            .where(TimeOff.do_datetime >= now)
            .order_by(TimeOff.od_datetime)
        ).all()
        return [_timeoff_dto(row) for row in rows]


def delete_time_off(session_factory: Callable[[], Session], time_off_id: int) -> None:
    """Trajno ukloni blokadu."""
    with session_factory() as session:
        block = session.get(TimeOff, time_off_id)
        if block is None:
            raise ValueError(f"blokada {time_off_id} nije pronađena")
        session.delete(block)
        session.commit()


def _check_timeoff_overlap(
    session: Session,
    doctor_id: int,
    start: datetime,
    end: datetime,
) -> None:
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status == AppointmentStatus.SCHEDULED,
        Appointment.start_time < end,
        Appointment.end_time > start,
    )
    if session.scalar(stmt) is not None:
        raise OverlapError(
            "blokada se preklapa sa postojećim zakazanim terminom — "
            "pomjerite ili otkažite termin prije kreiranja blokade"
        )


def _timeoff_dto(block: TimeOff) -> TimeOffDTO:
    assert block.doctor is not None
    return TimeOffDTO(
        id=block.id,
        doctor_id=block.doctor_id,
        doctor_name=block.doctor.ime,
        start=block.od_datetime,
        end=block.do_datetime,
        reason=block.razlog or "",
    )
