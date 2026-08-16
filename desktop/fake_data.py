"""Privremeni in-memory fake podatkovni sloj za DENT-002.

Namjerno plain Python (``@dataclass``), bez SQLAlchemy. Kad DENT-001 (šema)
bude merge-ovan, GUI se povezuje na prave modele kroz servisni sloj u
zasebnom budućem zadatku — ne kroz DENT-002.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# IANA zona (ne fiksni UTC offset) — DST bi inače pomjerio prikaz.
SARAJEVO = ZoneInfo("Europe/Sarajevo")
DEFAULT_DURATION_MINUTES = 30


@dataclass
class Appointment:
    """Termin u fake sloju. ``service`` je naziv usluge (string), ne FK."""

    id: int
    patient_name: str
    phone: str
    email: str
    service: str
    note: str
    start: datetime
    end: datetime


class FakeStore:
    """In-memory repozitorijum termina — zamjena za budući servisni sloj."""

    DEFAULT_SERVICES = [
        "Kontrola",
        "Čišćenje kamenca",
        "Plomba",
        "Vađenje zuba",
        "Izbjeljivanje",
    ]

    def __init__(
        self,
        appointments: list[Appointment] | None = None,
        services: list[str] | None = None,
    ):
        self._appointments: dict[int, Appointment] = {}
        self._services = (
            list(services) if services is not None else list(self.DEFAULT_SERVICES)
        )
        self._next_id = 1
        for appt in appointments or []:
            self.add(appt)

    def add(self, appt: Appointment) -> Appointment:
        if appt.id <= 0:
            appt.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, appt.id + 1)
        self._appointments[appt.id] = appt
        return appt

    def create(
        self,
        patient_name: str,
        phone: str,
        email: str,
        service: str,
        note: str,
        start: datetime,
        end: datetime,
    ) -> Appointment:
        return self.add(
            Appointment(
                id=0,
                patient_name=patient_name,
                phone=phone,
                email=email,
                service=service,
                note=note,
                start=start,
                end=end,
            )
        )

    def get(self, appt_id: int) -> Appointment | None:
        return self._appointments.get(appt_id)

    def all(self) -> list[Appointment]:
        return sorted(self._appointments.values(), key=lambda a: a.start)

    def move(self, appt_id: int, new_start: datetime, new_end: datetime) -> Appointment:
        appt = self._appointments[appt_id]
        appt.start = new_start
        appt.end = new_end
        return appt

    def services(self) -> list[str]:
        return list(self._services)

    @classmethod
    def seeded(cls, week_start: date) -> FakeStore:
        """Store sa nekoliko primjer termina unutar date sedmice (za prvi prikaz)."""
        store = cls()

        def at(day_offset: int, hour: int, minute: int = 0) -> datetime:
            day = week_start + timedelta(days=day_offset)
            return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SARAJEVO)

        store.create(
            "Marko Marković", "065/123-456", "marko@example.com",
            "Kontrola", "Prva posjeta",
            at(0, 9), at(0, 9, DEFAULT_DURATION_MINUTES),
        )
        store.create(
            "Jelena Jovanović", "066/234-567", "jelena@example.com",
            "Plomba", "",
            at(1, 11), at(1, 11, DEFAULT_DURATION_MINUTES),
        )
        store.create(
            "Petar Petrović", "065/345-678", "petar@example.com",
            "Čišćenje kamenca", "Osjetljivi zubi",
            at(3, 14), at(3, 14, DEFAULT_DURATION_MINUTES),
        )
        return store
