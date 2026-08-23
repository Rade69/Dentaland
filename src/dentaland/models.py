"""Dentaland — SQLAlchemy modeli za Fazu 0.

Šema je tačno prepisana iz ``docs/dentaland-razvojni-plan-v3.1.md``
(sekcija "Faza 0 — Šema baze"). Ovdje se ne dizajnira ništa novo.
"""

from __future__ import annotations

import enum
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    TypeDecorator,
    false,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Zajednička baza za sve modele."""


class AppointmentStatus(enum.StrEnum):
    """Status termina definisan od Faze 0.

    ``PENDING``/``REJECTED`` su Faza 1 aditivna dopuna (16.8.2026) — javni
    zahtjev sa web forme ulazi kao ``PENDING`` dok ga osoblje ne potvrdi
    (``SCHEDULED``) ili odbije (``REJECTED``). Postojeće vrijednosti se ne
    mijenjaju.
    """

    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


def utcnow() -> datetime:
    """Trenutno vrijeme kao timezone-aware UTC."""
    return datetime.now(UTC)


class TZDateTime(TypeDecorator):
    """DateTime koji prihvata samo timezone-aware vrijednosti.

    Naivan datetime se odbacuje (``ValueError``). Vrijednost se normalizuje na
    UTC prije upisa, a pri čitanju se vraća kao timezone-aware UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"očekivan datetime, dobijen {type(value).__name__}")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naivan datetime nije dozvoljen — koristi timezone-aware vrijednost")
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ime: Mapped[str] = mapped_column(String(200), nullable=False)
    aktivan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    working_hours: Mapped[list[WorkingHours]] = relationship(back_populates="doctor")
    time_offs: Mapped[list[TimeOff]] = relationship(back_populates="doctor")
    appointments: Mapped[list[Appointment]] = relationship(back_populates="doctor")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    naziv: Mapped[str] = mapped_column(String(200), nullable=False)
    trajanje_min: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    appointments: Mapped[list[Appointment]] = relationship(back_populates="service")


class WorkingHours(Base):
    __tablename__ = "working_hours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    # ISO dan u sedmici: 1 = ponedjeljak, ..., 7 = nedjelja.
    dan_u_sedmici: Mapped[int] = mapped_column(Integer, nullable=False)
    od_local: Mapped[time] = mapped_column(Time, nullable=False)
    do_local: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    doctor: Mapped[Doctor] = relationship(back_populates="working_hours")


class TimeOff(Base):
    __tablename__ = "time_off"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    od_datetime: Mapped[datetime] = mapped_column(TZDateTime(), nullable=False)
    do_datetime: Mapped[datetime] = mapped_column(TZDateTime(), nullable=False)
    razlog: Mapped[str | None] = mapped_column(String(500), nullable=True)

    doctor: Mapped[Doctor] = relationship(back_populates="time_offs")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), nullable=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    ime: Mapped[str] = mapped_column(String(200), nullable=False)
    telefon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    napomena: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Datum koji je pacijent tražio na javnoj formi — nezavisan od start_time,
    # jer se tačno vrijeme ne bira online (vidi docs/dentaland-javna-forma-spec.md).
    # Popunjen za PENDING zahtjeve; NULL za termine unesene direktno u ordinaciji.
    requested_date: Mapped[date | None] = mapped_column(nullable=True)
    # start_time/end_time su nepoznati dok je status PENDING — osoblje ih
    # postavlja pri potvrdi zahtjeva. Uvijek popunjeni za SCHEDULED i dalje.
    start_time: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            name="appointment_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
    )
    is_manual_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    # Aditivna dopuna (DENT-012, 17.8.2026) — nezavisne od status enuma:
    # termin može biti SCHEDULED, potvrđen, i još nije stigao sve
    # istovremeno. NULL = "nepoznato/nije se desilo", ne "sada". Ništa u
    # ovom trenutku ne popunjava ove kolone (šema ide ispred UI-ja koji
    # će ih koristiti) — vidi agent_reports/2026-08-17-DENT-012-plan.md.
    confirmed_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    # Aditivna dopuna (DENT-022, 23.8.2026) — dedup oznaka za email
    # podsjetnik (DENT-020). NULL = podsjetnik još nije poslan. Postavlja
    # ga isključivo send_due_appointment_reminders() nakon best-effort
    # slanja (bez obzira na SMTP ishod — vidi
    # agent_reports/2026-08-23-DENT-022-plan.md).
    reminder_sent_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime(), nullable=False, default=utcnow, onupdate=utcnow
    )

    doctor: Mapped[Doctor | None] = relationship(back_populates="appointments")
    service: Mapped[Service | None] = relationship(back_populates="appointments")
