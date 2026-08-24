"""Doctor/Service/WorkingHours administracija (REF-03).

Vlasnik postavki ordinacije: aktivacija doktora, CRUD usluga i administracija
radnog vremena. Izdvojeno iz ``booking.py`` (koji je sada tanak facade).

``add_service``/``update_service`` vraćaju ``ServiceOptionDTO`` — read-model
živi u ``appointments.py`` (tamo je potreban appointment editoru), pa ovaj
modul zavisi od ``appointments.py`` (jednosmjerna zavisnost, bez ciklusa).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from dentaland.models import Doctor, Service, WorkingHours
from dentaland.services.appointments import ServiceOptionDTO

DEFAULT_DOCTORS = ["Ljubo", "Zorka", "Ana"]
DEFAULT_SERVICES = [
    ("Kontrola", 30, 10),
    ("Čišćenje kamenca", 45, 10),
    ("Plomba", 60, 15),
    ("Vađenje zuba", 45, 15),
    ("Izbjeljivanje", 90, 15),
]


@dataclass
class DoctorDTO:
    id: int
    ime: str
    aktivan: bool = True


@dataclass
class WorkingHoursDTO:
    """Jedan interval radnog vremena doktora (split shift = više intervala)."""

    dan_u_sedmici: int
    od_local: time
    do_local: time


def doctors(session_factory: Callable[[], Session]) -> list[DoctorDTO]:
    """Aktivni doktori (za scheduler/editor dropdown)."""
    with session_factory() as session:
        rows = session.scalars(
            select(Doctor).where(Doctor.aktivan.is_(True)).order_by(Doctor.id)
        ).all()
        return [DoctorDTO(id=d.id, ime=d.ime) for d in rows]


def list_doctors(session_factory: Callable[[], Session]) -> list[DoctorDTO]:
    """Svi doktori (aktivan + neaktivan), za postavke."""
    with session_factory() as session:
        rows = session.scalars(select(Doctor).order_by(Doctor.id)).all()
        return [DoctorDTO(id=d.id, ime=d.ime, aktivan=d.aktivan) for d in rows]


def set_doctor_active(
    session_factory: Callable[[], Session], doctor_id: int, active: bool
) -> DoctorDTO:
    """Aktiviraj/deaktiviraj doktora — istorija termina ostaje netaknuta."""
    with session_factory() as session:
        doctor = session.get(Doctor, doctor_id)
        if doctor is None:
            raise ValueError(f"nepoznat doktor: {doctor_id}")
        doctor.aktivan = active
        session.commit()
        return DoctorDTO(id=doctor.id, ime=doctor.ime, aktivan=doctor.aktivan)


def add_service(
    session_factory: Callable[[], Session], naziv: str, trajanje_min: int, buffer_min: int
) -> ServiceOptionDTO:
    """Dodaj uslugu; validacija: naziv ne-prazan, trajanje>0, buffer>=0."""
    naziv = naziv.strip()
    if not naziv:
        raise ValueError("naziv usluge ne smije biti prazan")
    if trajanje_min <= 0:
        raise ValueError("trajanje usluge mora biti veće od 0 minuta")
    if buffer_min < 0:
        raise ValueError("buffer ne smije biti negativan")
    with session_factory() as session:
        service = Service(naziv=naziv, trajanje_min=trajanje_min, buffer_min=buffer_min)
        session.add(service)
        session.commit()
        return ServiceOptionDTO(
            id=service.id,
            naziv=service.naziv,
            trajanje_min=service.trajanje_min,
            buffer_min=service.buffer_min,
        )


def update_service(
    session_factory: Callable[[], Session],
    service_id: int,
    naziv: str,
    trajanje_min: int,
    buffer_min: int,
) -> ServiceOptionDTO:
    """Uredi uslugu; promjena trajanja utiče na nove termine."""
    naziv = naziv.strip()
    if not naziv:
        raise ValueError("naziv usluge ne smije biti prazan")
    if trajanje_min <= 0:
        raise ValueError("trajanje usluge mora biti veće od 0 minuta")
    if buffer_min < 0:
        raise ValueError("buffer ne smije biti negativan")
    with session_factory() as session:
        service = session.get(Service, service_id)
        if service is None:
            raise ValueError(f"nepoznata usluga: {service_id}")
        service.naziv = naziv
        service.trajanje_min = trajanje_min
        service.buffer_min = buffer_min
        session.commit()
        return ServiceOptionDTO(
            id=service.id,
            naziv=service.naziv,
            trajanje_min=service.trajanje_min,
            buffer_min=service.buffer_min,
        )


def list_working_hours(
    session_factory: Callable[[], Session], doctor_id: int
) -> list[WorkingHoursDTO]:
    """Intervali radnog vremena doktora, sortirani po danu i početku."""
    with session_factory() as session:
        rows = session.scalars(
            select(WorkingHours)
            .where(WorkingHours.doctor_id == doctor_id)
            .order_by(WorkingHours.dan_u_sedmici, WorkingHours.od_local)
        ).all()
        return [
            WorkingHoursDTO(
                dan_u_sedmici=row.dan_u_sedmici,
                od_local=row.od_local,
                do_local=row.do_local,
            )
            for row in rows
        ]


def set_working_hours(
    session_factory: Callable[[], Session],
    doctor_id: int,
    dan_u_sedmici: int,
    intervals: list[tuple[time, time]],
) -> None:
    """Postavi radno vrijeme doktora za jedan dan (split shift).

    Zamjenjuje postojeće intervale za taj dan. Validacija: dan 1..7,
    svaki interval od<do, intervali se ne preklapaju.
    """
    if not 1 <= dan_u_sedmici <= 7:
        raise ValueError("dan u sedmici mora biti 1..7")
    normalized: list[tuple[time, time]] = []
    for od_local, do_local in intervals:
        if do_local <= od_local:
            raise ValueError("kraj intervala mora biti poslije početka")
        normalized.append((od_local, do_local))
    normalized.sort(key=lambda pair: pair[0])
    for left, right in zip(normalized, normalized[1:], strict=False):
        if right[0] < left[1]:
            raise ValueError("intervali radnog vremena se ne smiju preklapati")
    with session_factory() as session:
        doctor = session.get(Doctor, doctor_id)
        if doctor is None:
            raise ValueError(f"nepoznat doktor: {doctor_id}")
        for row in session.scalars(
            select(WorkingHours).where(
                WorkingHours.doctor_id == doctor_id,
                WorkingHours.dan_u_sedmici == dan_u_sedmici,
            )
        ).all():
            session.delete(row)
        for od_local, do_local in normalized:
            session.add(
                WorkingHours(
                    doctor_id=doctor_id,
                    dan_u_sedmici=dan_u_sedmici,
                    od_local=od_local,
                    do_local=do_local,
                    timezone="Europe/Sarajevo",
                )
            )
        session.commit()


def ensure_seed_data(session_factory: Callable[[], Session]) -> None:
    """Popuni bazu početnim doktorima i uslugama ako je prazna (idempotentno)."""
    with session_factory() as session:
        if session.scalar(select(Doctor)) is None:
            session.add_all(Doctor(ime=name) for name in DEFAULT_DOCTORS)
        if session.scalar(select(Service)) is None:
            session.add_all(
                Service(naziv=naziv, trajanje_min=trajanje, buffer_min=buffer)
                for naziv, trajanje, buffer in DEFAULT_SERVICES
            )
        session.commit()
