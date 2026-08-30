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
    true,
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

    ``impl = DateTime(timezone=True)`` (DENT-IMPROVE-019) — BEZ ovoga Postgres
    kolona je ``timestamp without time zone``, pa Postgres pri upisu tz-aware
    vrijednosti prvo konvertuje u sesijsku ``TimeZone`` (server default) PA TEK
    ONDA odbaci oznaku zone — tiho pomjera upisano vrijeme za offset servera.
    Otkriveno 30.8.2026 (DENT-IMPROVE-018 end-to-end test, vidi
    ``agent_reports/DENT-IMPROVE-019-task-contract.md``): 11:00 UTC upisano,
    13:00 UTC pročitano nazad na serveru sa ``TimeZone=Europe/Berlin``.
    """

    impl = DateTime(timezone=True)
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
        return value.astimezone(UTC)


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
    # Aditivna dopuna (DENT-IMPROVE-018, 30.8.2026) — Telegram opt-in.
    # telegram_link_token_hash/expires_at su uže-namjenski jednokratni
    # token (isti obrazac kao Session.token_hash) za /start deep link;
    # brišu se nakon uspješne upotrebe. telegram_chat_id/subscribed_at
    # se popunjavaju TEK kad pacijent stvarno klikne link i pošalje
    # /start botu — do tada su NULL. Vidi src/dentaland/services/telegram.py.
    telegram_link_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram_link_token_expires_at: Mapped[datetime | None] = mapped_column(
        TZDateTime(), nullable=True
    )
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram_subscribed_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime(), nullable=False, default=utcnow, onupdate=utcnow
    )

    doctor: Mapped[Doctor | None] = relationship(back_populates="appointments")
    service: Mapped[Service | None] = relationship(back_populates="appointments")


class UserRole(enum.StrEnum):
    """Uloge osoblja (DENT-IMPROVE-013) — vidi ``docs/dentaland-razvojni-plan-v3.1.md``
    sekcija "RBAC" za punu semantiku. ``ADMIN`` NAMJERNO ne dobija
    automatski pravo na operativne radnje (confirm/reject) samo zato što
    administrira sistem — permission check je uvijek eksplicitan po
    endpointu/servisu, nikad implicitan preko "viša uloga uvijek prolazi".
    """

    RECEPTION = "RECEPTION"
    DENTIST = "DENTIST"
    ADMIN = "ADMIN"


class User(Base):
    """Individualni nalog zaposlenog (DENT-IMPROVE-013).

    Namjerno NEMA zajedničkog "admin" naloga za više zaposlenih — svaki
    zaposleni ima svoj red (v3.1: "audit ima smisla samo tako"). Nalozi se
    kreiraju isključivo preko ``scripts/create_user.py`` (CLI), ne kroz
    UI/API u ovoj fazi.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Argon2id hash (preko argon2-cffi) — NIKAD plaintext, NIKAD bcrypt/MD5/SHA-only.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), nullable=False, default=utcnow)

    sessions: Mapped[list[Session]] = relationship(back_populates="user")


class Session(Base):
    """Server-side sesija (DENT-IMPROVE-013).

    Isti sigurni token obrazac kao planirani cancel-link token
    (``CLAUDE.md``): sirov token je ``secrets.token_urlsafe(32)``, NIKAD
    upisan u bazu — čuva se samo SHA-256 heks hash (``token_hash``).
    ``revoked_at`` je eksplicitna invalidacija (logout, promjena lozinke)
    — red se NE briše, radi mogućeg budućeg audit uvida (DENT-IMPROVE-014).
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TZDateTime(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), nullable=False, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class AuditAction(enum.StrEnum):
    """Append-only audit akcije (DENT-IMPROVE-014) — TAČNO backlog "Minimum
    events" lista, ne šira v3.1 lista (``VIEW_PATIENT``,
    ``EXPORT_PERSONAL_DATA``, ``DELETE_OR_ANONYMIZE_PERSONAL_DATA``,
    ``VIEW_MEDICAL_DATA`` su van obima — nemaju odgovarajuću funkcionalnost
    u kodu još, dodaju se kad ta funkcionalnost postoji, ne unaprijed).

    ``CHANGE_ROLE`` je NAMJERNO dormant — definisana vrijednost, bez ijednog
    pozivaoca u kodu (nema role-change endpointa/UI-ja). Isti tretman kao
    ``EXCLUDE`` constraint u DENT-IMPROVE-012: definisano radi buduće
    kompatibilnosti, ne izgrađuje se funkcionalnost oko nje u ovom tasku.
    """

    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    CREATE_APPOINTMENT = "CREATE_APPOINTMENT"
    UPDATE_APPOINTMENT = "UPDATE_APPOINTMENT"
    CANCEL_APPOINTMENT = "CANCEL_APPOINTMENT"
    DELETE_APPOINTMENT = "DELETE_APPOINTMENT"
    CHANGE_ROLE = "CHANGE_ROLE"


class AuditEvent(Base):
    """Append-only audit zapis (DENT-IMPROVE-014) — v3.1 plan, sekcija
    "Audit log" (oko linije 267).

    **Append-only napomena**: ova tabela namjerno nema odgovarajuću
    ``update``/``delete`` funkciju bilo gdje u servisnom sloju
    (``src/dentaland/services/audit.py``) — append-only ponašanje se u
    ovom obimu postiže disciplinom (ne izlaganjem mutacionog API-ja), ne
    DB-nivo trigerom/permisijom. Proporcionalno veličini projekta (jedan
    VPS, jedna ordinacija) — vidi CLAUDE.md "Šta se namjerno ne gradi
    unaprijed". Direktan SQL UPDATE/DELETE na tabeli je i dalje tehnički
    moguć (nema DB-nivo brane), ali nijedan ugrađeni API poziv to ne radi
    slučajno.

    **`metadata_minimal` upozorenje**: mali JSON-enkodiran string koji
    pozivalac (budući `write_audit_event` pozivalac, npr. DENT-IMPROVE-014B/
    014C) popunjava. Pozivalac je ISKLJUČIVO odgovoran da ovdje nikad ne
    stavi lozinku/token/medicinski sadržaj/pun request body — ova klasa/
    `write_audit_event` NE validira niti sanitizuje sadržaj (v3.1: "audit
    log ne kopira medicinski sadržaj u metadata").

    ``actor_user_id`` je nullable — desktop app (Faza 0) nema koncept
    ulogovanog korisnika, pa će appointment-vezani audit zapisi
    (CREATE/UPDATE/CANCEL/DELETE_APPOINTMENT, iz DENT-IMPROVE-014C) uvijek
    imati ``actor_user_id=NULL``. Ovo je prihvaćeno ograničenje (Radovanova
    odluka, 27.8.2026), ne nedostatak ovog modela.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[AuditAction] = mapped_column(
        Enum(
            AuditAction,
            name="audit_action",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(TZDateTime(), nullable=False, default=utcnow)
    # Backend popunjava (npr. FastAPI request-scoped korelacioni ID);
    # desktop poziv (nema HTTP request) uvijek ostavlja NULL.
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Backend popunjava iz `Request.client.host`; desktop poziv uvijek NULL.
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_minimal: Mapped[str | None] = mapped_column(Text, nullable=True)
