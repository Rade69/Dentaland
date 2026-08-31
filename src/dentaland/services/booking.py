"""Servisni sloj za termine — tanak compatibility facade (REF-03).

``AppointmentService`` je sada SAMO facade: svaka javna metoda delegira ka
jednom od fokusiranih modula (``appointments`` / ``availability`` /
``settings`` / ``requests``). Nova poslovna logika se NE dodaje ovdje — ide
u odgovarajući modul.

Klasa i DTO-ovi ostaju importabilni iz ``dentaland.services.booking`` radi
backward-compat sa GUI-jem (``desktop``) i ``print_schedule.py``, koji rade
``from dentaland.services.booking import AppointmentService``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from dentaland.models import Base, Doctor
from dentaland.services import appointments, availability, settings
from dentaland.services.appointments import AppointmentDTO, ServiceOptionDTO
from dentaland.services.availability import (
    CalendarBlockDTO,
    OverlapError,  # noqa: F401 — re-eksport kanonične klase (backward-compat)
    TimeOffDTO,
)
from dentaland.services.requests import (
    RequestDTO,
    confirm_request,
    list_pending,
    reject_request,
)
from dentaland.services.settings import DoctorDTO, WorkingHoursDTO, ensure_seed_data


class AppointmentService:
    """Facade nad appointment/availability/settings/requests servisima.

    ``session_factory`` mora vraćati ``Session`` konfigurisan sa
    ``expire_on_commit=False`` da bi DTO konstrukcija nakon commit-a bila
    pouzdana (bez dodatnog lazy refresh-a).
    """

    def __init__(self, session_factory: Callable[[], Session], doctor_id: int | None = None):
        self._session_factory = session_factory
        self.doctor_id = doctor_id

    @classmethod
    def from_sqlite(cls, path: str) -> AppointmentService:
        """Kreira servis nad SQLite bazom, uz seed ako je baza prazna."""
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(engine, expire_on_commit=False)
        ensure_seed_data(session_factory)
        with session_factory() as session:
            first = session.scalar(select(Doctor).order_by(Doctor.id))
        return cls(session_factory, doctor_id=first.id if first is not None else None)

    @classmethod
    def from_database_url(cls, url: str) -> AppointmentService:
        """Kreira servis nad POSTOJEĆOM bazom preko proizvoljnog SQLAlchemy
        URL-a (npr. Postgres na udaljenom serveru, preko SSH tunela).

        Za razliku od ``from_sqlite``: NE zove ``Base.metadata.create_all``
        (šema se pretpostavlja već migrirana preko alembic-a — ovo je za
        povezivanje na postojeću bazu, ne kreiranje nove) niti
        ``ensure_seed_data`` (ne upisuje ništa u tuđu/udaljenu bazu samo
        zato što se otvara viewer)."""
        engine = create_engine(url)
        session_factory = sessionmaker(engine, expire_on_commit=False)
        with session_factory() as session:
            first = session.scalar(select(Doctor).order_by(Doctor.id))
        return cls(session_factory, doctor_id=first.id if first is not None else None)

    def set_doctor(self, doctor_id: int) -> None:
        self.doctor_id = doctor_id

    def doctors(self) -> list[DoctorDTO]:
        return settings.doctors(self._session_factory)

    def services(self) -> list[str]:
        return appointments.list_service_names(self._session_factory)

    def create(
        self,
        patient_name: str,
        phone: str,
        email: str,
        service: str,
        note: str,
        start: datetime,
        end: datetime,
    ) -> AppointmentDTO:
        doctor_id = self._require_doctor()
        return appointments.create_appointment(
            self._session_factory,
            doctor_id,
            patient_name,
            phone,
            email,
            service,
            note,
            start,
            end,
        )

    def update(
        self,
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
        return appointments.update_appointment(
            self._session_factory,
            appt_id,
            patient_name=patient_name,
            phone=phone,
            email=email,
            doctor_id=doctor_id,
            service=service,
            note=note,
            start=start,
            end=end,
        )

    def get(self, appt_id: int) -> AppointmentDTO | None:
        return appointments.get_appointment(self._session_factory, appt_id)

    def all(self) -> list[AppointmentDTO]:
        doctor_id = self._require_doctor()
        return appointments.list_appointments(self._session_factory, doctor_id)

    def all_combined(self) -> list[AppointmentDTO]:
        return appointments.all_combined_appointments(self._session_factory)

    def appointments_for_range(
        self,
        range_start: datetime,
        range_end: datetime,
        doctor_id: int | None = None,
    ) -> list[AppointmentDTO]:
        return appointments.appointments_for_range(
            self._session_factory, range_start, range_end, doctor_id=doctor_id
        )

    def mark_arrived(self, appt_id: int) -> AppointmentDTO:
        return appointments.mark_arrived(self._session_factory, appt_id)

    def unmark_arrived(self, appt_id: int) -> AppointmentDTO:
        return appointments.unmark_arrived(self._session_factory, appt_id)

    def mark_confirmed(self, appt_id: int) -> AppointmentDTO:
        return appointments.mark_confirmed(self._session_factory, appt_id)

    def cancel(self, appt_id: int) -> AppointmentDTO:
        return appointments.cancel_appointment(self._session_factory, appt_id)

    def delete(self, appt_id: int) -> None:
        return appointments.delete_appointment(self._session_factory, appt_id)

    def mark_completed(self, appt_id: int) -> AppointmentDTO:
        return appointments.mark_completed(self._session_factory, appt_id)

    def mark_no_show(self, appt_id: int) -> AppointmentDTO:
        return appointments.mark_no_show(self._session_factory, appt_id)

    def awaiting_confirmation(self) -> list[AppointmentDTO]:
        return appointments.awaiting_confirmation(self._session_factory)

    def cancelled_today(self, day: date | None = None) -> list[AppointmentDTO]:
        return appointments.cancelled_today(self._session_factory, day)

    def pending_requests(self) -> list[RequestDTO]:
        return list_pending(self._session_factory)

    def confirm_pending(
        self, request_id: int, doctor_id: int, service_id: int, start: datetime
    ) -> None:
        confirm_request(self._session_factory, request_id, doctor_id, service_id, start)

    def reject_pending(self, request_id: int) -> None:
        reject_request(self._session_factory, request_id)

    def service_choices(self) -> list[tuple[int, str]]:
        return appointments.service_choices(self._session_factory)

    def service_options(self) -> list[ServiceOptionDTO]:
        return appointments.service_options(self._session_factory)

    def time_off_for_week(self, week_start: date) -> list[CalendarBlockDTO]:
        return availability.time_off_for_week(self._session_factory, week_start)

    def breaks_for_week(self, week_start: date) -> list[CalendarBlockDTO]:
        return availability.breaks_for_week(self._session_factory, week_start)

    def schedule_snapshot(
        self,
        range_start: datetime,
        range_end: datetime,
        week_start: date,
        doctor_id: int | None = None,
    ) -> tuple[list[AppointmentDTO], list[CalendarBlockDTO]]:
        return appointments.schedule_snapshot(
            self._session_factory, range_start, range_end, week_start, doctor_id=doctor_id
        )

    def create_time_off(
        self,
        doctor_id: int,
        start: datetime,
        end: datetime,
        reason: str | None = None,
    ) -> TimeOffDTO:
        return availability.create_time_off(
            self._session_factory, doctor_id, start, end, reason
        )

    def list_time_off(self) -> list[TimeOffDTO]:
        return availability.list_time_off(self._session_factory)

    def delete_time_off(self, time_off_id: int) -> None:
        return availability.delete_time_off(self._session_factory, time_off_id)

    def move(self, appt_id: int, new_start: datetime, new_end: datetime) -> AppointmentDTO:
        return appointments.move_appointment(self._session_factory, appt_id, new_start, new_end)

    def list_doctors(self) -> list[DoctorDTO]:
        return settings.list_doctors(self._session_factory)

    def set_doctor_active(self, doctor_id: int, active: bool) -> DoctorDTO:
        return settings.set_doctor_active(self._session_factory, doctor_id, active)

    def add_service(
        self, naziv: str, trajanje_min: int, buffer_min: int
    ) -> ServiceOptionDTO:
        return settings.add_service(self._session_factory, naziv, trajanje_min, buffer_min)

    def update_service(
        self, service_id: int, naziv: str, trajanje_min: int, buffer_min: int
    ) -> ServiceOptionDTO:
        return settings.update_service(
            self._session_factory, service_id, naziv, trajanje_min, buffer_min
        )

    def list_working_hours(self, doctor_id: int) -> list[WorkingHoursDTO]:
        return settings.list_working_hours(self._session_factory, doctor_id)

    def set_working_hours(
        self,
        doctor_id: int,
        dan_u_sedmici: int,
        intervals: list[tuple[time, time]],
    ) -> None:
        return settings.set_working_hours(
            self._session_factory, doctor_id, dan_u_sedmici, intervals
        )

    def _require_doctor(self) -> int:
        if self.doctor_id is None:
            raise ValueError("nije odabran doktor")
        return self.doctor_id
