"""Servisni sloj za termine (Faza 0).

Drop-in zamjena za ``desktop.fake_data.FakeStore`` istog oblika interfejsa
(``create``/``get``/``all``/``move``/``services``), ali podržan SQLAlchemy
modelima iz DENT-001. Field-name prevod (fake ↔ model):

* ``patient_name`` ↔ ``ime``, ``phone`` ↔ ``telefon``, ``email`` ↔ ``email``
* ``service`` (naziv) ↔ ``service_id`` → ``Service.naziv``
* ``note`` ↔ ``napomena``, ``start`` ↔ ``start_time``, ``end`` ↔ ``end_time``

GUI nikad ne dobija SQLAlchemy objekte — servis vraća plain DTO dataclasses.

``doctor_id``/``service_id``/``start_time``/``end_time`` su nullable na
nivou modela (DENT-007 — javni zahtjev stiže bez njih dok nije potvrđen,
vidi ``src/dentaland/services/requests.py``), ali svaki red kojim ovaj
modul (booking.py) rukuje je uvijek ili tek kreiran ovdje (sva četiri polja
se postavljaju atomski u ``create()``) ili već ima status različit od
``PENDING`` — što po konstrukciji znači da su sva četiri polja popunjena.
``assert`` pozivi ispod postoje da to i mypy zna, ne mijenjaju runtime
ponašanje u normalnom slučaju.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from dentaland.models import Appointment, AppointmentStatus, Base, Doctor, Service

DEFAULT_DOCTORS = ["Ljubo", "Zorka", "Ana"]
DEFAULT_SERVICES = [
    ("Kontrola", 30, 10),
    ("Čišćenje kamenca", 45, 10),
    ("Plomba", 60, 15),
    ("Vađenje zuba", 45, 15),
    ("Izbjeljivanje", 90, 15),
]


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


@dataclass
class DoctorDTO:
    id: int
    ime: str


class OverlapError(Exception):
    """Dva aktivna termina istog doktora se vremenski preklapaju."""


class AppointmentService:
    """CRUD termina nad SQLAlchemy modelima, ograničen na jednog doktora.

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

    def set_doctor(self, doctor_id: int) -> None:
        self.doctor_id = doctor_id

    def doctors(self) -> list[DoctorDTO]:
        with self._session_factory() as session:
            doctors = session.scalars(
                select(Doctor).where(Doctor.aktivan.is_(True)).order_by(Doctor.id)
            ).all()
            return [DoctorDTO(id=d.id, ime=d.ime) for d in doctors]

    def services(self) -> list[str]:
        with self._session_factory() as session:
            services = session.scalars(select(Service).order_by(Service.naziv)).all()
            return [s.naziv for s in services]

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
        with self._session_factory() as session:
            self._check_overlap(session, doctor_id, start, end)
            service_obj = self._get_service(session, service)
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
            return self._to_dto(appt, service_obj.naziv)

    def get(self, appt_id: int) -> AppointmentDTO | None:
        with self._session_factory() as session:
            appt = session.scalar(
                select(Appointment).where(Appointment.id == appt_id)
            )
            if appt is None:
                return None
            return self._to_dto(appt, self._service_name(appt))

    def all(self) -> list[AppointmentDTO]:
        doctor_id = self._require_doctor()
        with self._session_factory() as session:
            appts = session.scalars(
                select(Appointment)
                .where(Appointment.doctor_id == doctor_id)
                .order_by(Appointment.start_time)
            ).all()
            return [self._to_dto(a, self._service_name(a)) for a in appts]

    def all_combined(self) -> list[AppointmentDTO]:
        """Termini svih doktora odjednom (za kombinovani sedmični prikaz)."""
        with self._session_factory() as session:
            appts = session.scalars(
                select(Appointment).order_by(Appointment.start_time)
            ).all()
            return [self._to_dto(a, self._service_name(a)) for a in appts]

    def move(self, appt_id: int, new_start: datetime, new_end: datetime) -> AppointmentDTO:
        with self._session_factory() as session:
            appt = session.scalar(
                select(Appointment).where(Appointment.id == appt_id)
            )
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            assert appt.doctor_id is not None, "move() radi samo nad već dodijeljenim terminima"
            # Overlap se provjerava za doktora SAMOG termina, ne za self.doctor_id
            # — drag&drop mora raditi i u kombinovanom prikazu (DENT-006).
            self._check_overlap(
                session, appt.doctor_id, new_start, new_end, exclude_id=appt_id
            )
            appt.start_time = new_start
            appt.end_time = new_end
            session.commit()
            return self._to_dto(appt, self._service_name(appt))

    # ---- interne ----

    def _require_doctor(self) -> int:
        if self.doctor_id is None:
            raise ValueError("nije odabran doktor")
        return self.doctor_id

    def _get_service(self, session: Session, service_name: str) -> Service:
        service = session.scalar(select(Service).where(Service.naziv == service_name))
        if service is None:
            raise ValueError(f"nepoznata usluga: {service_name}")
        return service

    def _check_overlap(
        self,
        session: Session,
        doctor_id: int,
        start: datetime,
        end: datetime,
        exclude_id: int | None = None,
    ) -> None:
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

    @staticmethod
    def _service_name(appt: Appointment) -> str:
        assert appt.service is not None, "termin bez usluge nije nadležnost booking.py"
        return appt.service.naziv

    @staticmethod
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
        )


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
