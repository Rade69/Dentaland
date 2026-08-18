"""Servisni sloj za podatke o rasporedu namijenjene štampi (DENT-015).

Ovaj modul priprema "za-štampu spreman" prikaz dnevnog/sedmičnog
rasporeda za GUI/rendering sloj (DENT-016). Čist servisni sloj — BEZ Qt
zavisnosti, samo plain dataclasses.

Minimizacija podataka je ovdje STRUKTURNA, ne stvar discipline prikaza:
``PrintScheduleEntry``/``PrintScheduleBlock`` u tipu uopšte NEMAJU polja
za telefon, email ili napomenu, pa curenje ličnih podataka na papir/PDF
nije ni moguće kroz ovaj kod (isti obrazac kao ``backend/notifications.py``
iz DENT-011). Usluga se prikazuje (potvrđena poslovna odluka), doktor se
prikazuje, ali kontakt-podaci i napomene NIKAD ne ulaze u ove tipove.

Raspored je OPERATIVNI, ne istorijski: ``CANCELLED`` i ``NO_SHOW`` termini
se isključuju (štampan papir je za današnji rad, ne za arhivu).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dentaland.models import AppointmentStatus
from dentaland.services.booking import AppointmentDTO, AppointmentService

SARAJEVO = ZoneInfo("Europe/Sarajevo")

# Mora pratiti WeekView.DAY_COUNT (desktop/views/week_view.py) — Pon–Sub.
# Ne pretpostavljati 5 ni 7 dana; ovo je trenutna odluka prikaza.
WEEK_DAY_COUNT = 6

_DAY_NAMES_FULL = [
    "Ponedjeljak",
    "Utorak",
    "Srijeda",
    "Četvrtak",
    "Petak",
    "Subota",
    "Nedjelja",
]

# Isti skraćeni oblik kao WeekView.DAY_NAMES (desktop/views/week_view.py) —
# dosljednost sa kalendarom, ne izmišljati novu konvenciju za štampu.
_DAY_NAMES_SHORT = ["Pon", "Uto", "Sri", "Čet", "Pet", "Sub", "Ned"]

# CalendarBlockDTO.label stiže velikim slovima iz booking.py — za štampu
# normalizujemo poznate labele u čitljiviji oblik (custom razlog ostaje kako je).
_BLOCK_LABELS = {
    "VAN ORDINACIJE": "Van ordinacije",
    "PAUZA": "Pauza",
}


@dataclass
class PrintScheduleEntry:
    """Jedan termin u obliku za štampu.

    Namjerno BEZ phone/email/note polja — minimizacija podataka po dizajnu.

    ``day_label`` (npr. "Pon") je strukturno polje, ne dio ``time_range``
    stringa — GUI/rendering sloj (DENT-016) treba dan kao zaseban podatak
    za sedmični layout sa kolonama po danu, i ne smije parsirati string da
    bi ga dobio. Za dnevni raspored (``build_day_schedule``) svi entry/
    block imaju isti dan po definiciji — polje je i dalje popunjeno, samo
    se ne koristi za grupisanje.
    """

    time_range: str
    patient_name: str
    doctor_name: str
    service: str
    status_label: str
    day_label: str


@dataclass
class PrintScheduleBlock:
    """Neklikabilan raspon (odsustvo/pauza) u obliku za štampu."""

    time_range: str
    doctor_name: str
    label: str
    day_label: str


@dataclass
class PrintSchedule:
    """Rezultat jednog poziva — naslov + hronološki sortirani sadržaj."""

    title: str
    entries: list[PrintScheduleEntry]
    blocks: list[PrintScheduleBlock]


def build_day_schedule(service: AppointmentService, day: date) -> PrintSchedule:
    """Raspored za jedan dan (termini + odsustva/pauze tog dana)."""
    return PrintSchedule(
        title=_day_title(day),
        entries=_entries_for(service, day, day + timedelta(days=1)),
        blocks=_blocks_for(service, day, day + timedelta(days=1)),
    )


def build_week_schedule(service: AppointmentService, week_start: date) -> PrintSchedule:
    """Raspored za prikazanu sedmicu (Pon–Sub, ``WEEK_DAY_COUNT`` dana)."""
    range_end = week_start + timedelta(days=WEEK_DAY_COUNT)
    return PrintSchedule(
        title=_week_title(week_start, range_end),
        entries=_entries_for(service, week_start, range_end),
        blocks=_blocks_for(service, week_start, range_end),
    )


def _entries_for(
    service: AppointmentService, range_start: date, range_end: date
) -> list[PrintScheduleEntry]:
    dtos = [
        dto
        for dto in service.all_combined()
        if dto.status not in (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW)
        and range_start <= dto.start.astimezone(SARAJEVO).date() < range_end
    ]
    dtos.sort(key=lambda dto: dto.start)
    return [
        PrintScheduleEntry(
            time_range=_fmt_time_range(dto.start, dto.end),
            patient_name=dto.patient_name,
            doctor_name=dto.doctor_name,
            service=dto.service,
            status_label=_status_label(dto),
            day_label=_day_label(dto.start),
        )
        for dto in dtos
    ]


def _blocks_for(
    service: AppointmentService, range_start: date, range_end: date
) -> list[PrintScheduleBlock]:
    week_start = range_start - timedelta(days=range_start.isoweekday() - 1)
    doctor_names = _doctor_names(service)
    range_start_dt = datetime.combine(range_start, time.min, tzinfo=SARAJEVO)
    range_end_dt = datetime.combine(range_end, time.min, tzinfo=SARAJEVO)

    clipped: list[tuple[datetime, datetime, int, str]] = []
    for block in [*service.time_off_for_week(week_start), *service.breaks_for_week(week_start)]:
        if block.start >= range_end_dt or block.end <= range_start_dt:
            continue
        clipped.append(
            (
                max(block.start, range_start_dt),
                min(block.end, range_end_dt),
                block.doctor_id,
                block.label,
            )
        )
    clipped.sort(key=lambda item: item[0])
    return [
        PrintScheduleBlock(
            time_range=_fmt_time_range(start, end),
            doctor_name=doctor_names.get(doctor_id, ""),
            label=_BLOCK_LABELS.get(label, label),
            day_label=_day_label(start),
        )
        for start, end, doctor_id, label in clipped
    ]


def _doctor_names(service: AppointmentService) -> dict[int, str]:
    return {doctor.id: doctor.ime for doctor in service.doctors()}


def _status_label(dto: AppointmentDTO) -> str:
    """Srpski statusni tekst — IDENTIČAN statusnoj legendi iz DENT-009."""
    if dto.status == AppointmentStatus.COMPLETED:
        return "Završen"
    if dto.arrived_at is not None:
        return "Stigao"
    if dto.confirmed_at is not None:
        return "Potvrđen"
    return "Čeka potvrdu"


def _fmt_time_range(start: datetime, end: datetime) -> str:
    return f"{start.astimezone(SARAJEVO):%H:%M}–{end.astimezone(SARAJEVO):%H:%M}"


def _day_label(when: datetime) -> str:
    return _DAY_NAMES_SHORT[when.astimezone(SARAJEVO).isoweekday() - 1]


def _day_title(day: date) -> str:
    return f"{_DAY_NAMES_FULL[day.isoweekday() - 1]}, {day:%d.%m.%Y.}"


def _week_title(week_start: date, range_end: date) -> str:
    last_day = range_end - timedelta(days=1)
    return f"{week_start:%d.%m.} – {last_day:%d.%m.%Y.}"
