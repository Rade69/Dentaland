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
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from dentaland.models import (
    Appointment,
    AppointmentStatus,
    Base,
    Doctor,
    Service,
    TimeOff,
    WorkingHours,
    utcnow,
)
from dentaland.services.availability import OverlapError, validate_appointment_overlap
from dentaland.services.requests import (
    RequestDTO,
    confirm_request,
    list_pending,
    reject_request,
)

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
    status: AppointmentStatus
    confirmed_at: datetime | None
    arrived_at: datetime | None


@dataclass
class DoctorDTO:
    id: int
    ime: str
    aktivan: bool = True


@dataclass
class ServiceOptionDTO:
    """Stabilan read-model usluge za GUI (id, naziv, trajanje, buffer).

    Trajanje dolazi iz ``Service.trajanje_min`` — nikad se ne izmišlja ni
    hardkoduje na strani GUI-ja (Faza A redizajna).
    """

    id: int
    naziv: str
    trajanje_min: int
    buffer_min: int


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


@dataclass
class WorkingHoursDTO:
    """Jedan interval radnog vremena doktora (split shift = više intervala)."""

    dan_u_sedmici: int
    od_local: time
    do_local: time


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
        """Uredi postojeći termin — sva polja, sa overlap provjerom za novog doktora.

        Dozvoljeno samo za ``SCHEDULED`` termin (terminalna stanja su
        read-only). ``exclude_id=appt_id`` osigurava da termin pri editovanju
        ne vidi sam sebe kao preklapanje (isti obrazac kao ``move()``).
        """
        with self._session_factory() as session:
            appt = session.get(Appointment, appt_id)
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            if appt.status != AppointmentStatus.SCHEDULED:
                raise ValueError("samo zakazan termin može biti uređen")
            doctor = session.get(Doctor, doctor_id)
            if doctor is None:
                raise ValueError(f"nepoznat doktor: {doctor_id}")
            service_obj = self._get_service(session, service)
            self._check_overlap(session, doctor_id, start, end, exclude_id=appt_id)
            appt.ime = patient_name
            appt.telefon = phone
            appt.email = email
            appt.doctor_id = doctor_id
            appt.service_id = service_obj.id
            appt.napomena = note
            appt.start_time = start
            appt.end_time = end
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
                select(Appointment)
                .where(
                    Appointment.start_time.is_not(None),
                    Appointment.end_time.is_not(None),
                    Appointment.doctor_id.is_not(None),
                    Appointment.service_id.is_not(None),
                    Appointment.status.not_in(
                        [AppointmentStatus.PENDING, AppointmentStatus.REJECTED]
                    ),
                )
                .order_by(Appointment.start_time)
            ).all()
            return [self._to_dto(a, self._service_name(a)) for a in appts]

    def appointments_for_range(
        self,
        range_start: datetime,
        range_end: datetime,
        doctor_id: int | None = None,
    ) -> list[AppointmentDTO]:
        """Termini koji se vremenski preklapaju sa ``[range_start, range_end)``.

        Intervalska overlap semantika (isto kao ``validate_appointment_overlap``
        iz ``availability.py``): ``start_time < range_end AND end_time >
        range_start``. Doctor i Service se učitavaju ``selectinload``-om (bez
        N+1). ``doctor_id=None`` vraća sve doktore.
        """
        with self._session_factory() as session:
            stmt = (
                select(Appointment)
                .options(
                    selectinload(Appointment.doctor),
                    selectinload(Appointment.service),
                )
                .where(
                    Appointment.start_time.is_not(None),
                    Appointment.end_time.is_not(None),
                    Appointment.doctor_id.is_not(None),
                    Appointment.service_id.is_not(None),
                    Appointment.status.not_in(
                        [AppointmentStatus.PENDING, AppointmentStatus.REJECTED]
                    ),
                    Appointment.start_time < range_end,
                    Appointment.end_time > range_start,
                )
                .order_by(Appointment.start_time)
            )
            if doctor_id is not None:
                stmt = stmt.where(Appointment.doctor_id == doctor_id)
            appts = session.scalars(stmt).all()
            return [self._to_dto(a, self._service_name(a)) for a in appts]

    def mark_arrived(self, appt_id: int) -> AppointmentDTO:
        """Označi da je pacijent stigao; dozvoljeno samo za zakazan termin."""
        with self._session_factory() as session:
            appt = session.get(Appointment, appt_id)
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            if appt.status != AppointmentStatus.SCHEDULED:
                raise ValueError("samo zakazan termin može biti označen kao stigao")
            appt.arrived_at = utcnow()
            session.commit()
            return self._to_dto(appt, self._service_name(appt))

    def unmark_arrived(self, appt_id: int) -> AppointmentDTO:
        """Poništi "stigao" (npr. slučajan klik) — vrati termin na prethodni status."""
        with self._session_factory() as session:
            appt = session.get(Appointment, appt_id)
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            appt.arrived_at = None
            session.commit()
            return self._to_dto(appt, self._service_name(appt))

    def mark_confirmed(self, appt_id: int) -> AppointmentDTO:
        """Označi ručno unesen termin kao potvrđen (npr. nakon poziva pacijentu).

        Odvojeno od ``confirm_request`` (DENT-007) — ovo je za termine koje je
        osoblje unijelo direktno u kalendar (bez web zahtjeva), pa ``confirmed_at``
        nikad nije postavljen pri kreiranju (vidi ``create()``).
        """
        with self._session_factory() as session:
            appt = session.get(Appointment, appt_id)
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            if appt.status != AppointmentStatus.SCHEDULED:
                raise ValueError("samo zakazan termin može biti označen kao potvrđen")
            appt.confirmed_at = utcnow()
            session.commit()
            return self._to_dto(appt, self._service_name(appt))

    def cancel(self, appt_id: int) -> AppointmentDTO:
        """Otkaži zakazan termin (npr. pacijent odustao ili greška pri unosu)."""
        with self._session_factory() as session:
            appt = session.get(Appointment, appt_id)
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            if appt.status != AppointmentStatus.SCHEDULED:
                raise ValueError("samo zakazan termin može biti otkazan")
            appt.status = AppointmentStatus.CANCELLED
            session.commit()
            return self._to_dto(appt, self._service_name(appt))

    def delete(self, appt_id: int) -> None:
        """Trajno ukloni termin — isključivo za greškom kreiran zapis.

        Za razliku od ``cancel()`` (zapis ostaje u istoriji), ovo je
        nepovratan hard delete. Dozvoljeno za bilo koji status (greška u
        unosu se može otkriti i nakon što je termin već označen
        završenim/otkazanim) — nema status-provjere kao kod cancel/mark_*.

        FK provjera (DENT-DESKTOP-F plan): ništa u trenutnoj šemi ne
        referencira ``appointments.id`` kao strani ključ (Appointment ima
        FK-ove KA Doctor/Service, ne obrnuto), pa je prost DELETE bez
        cascade rizika.
        """
        with self._session_factory() as session:
            appt = session.get(Appointment, appt_id)
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            session.delete(appt)
            session.commit()

    def mark_completed(self, appt_id: int) -> AppointmentDTO:
        """Označi termin kao završen; dozvoljeno samo za zakazan termin."""
        with self._session_factory() as session:
            appt = session.get(Appointment, appt_id)
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            if appt.status != AppointmentStatus.SCHEDULED:
                raise ValueError("samo zakazan termin može biti označen kao završen")
            appt.status = AppointmentStatus.COMPLETED
            session.commit()
            return self._to_dto(appt, self._service_name(appt))

    def mark_no_show(self, appt_id: int) -> AppointmentDTO:
        """Označi termin kao 'nije došao'; dozvoljeno samo za zakazan termin."""
        with self._session_factory() as session:
            appt = session.get(Appointment, appt_id)
            if appt is None:
                raise ValueError(f"termin {appt_id} nije pronađen")
            if appt.status != AppointmentStatus.SCHEDULED:
                raise ValueError("samo zakazan termin može biti označen kao 'nije došao'")
            appt.status = AppointmentStatus.NO_SHOW
            session.commit()
            return self._to_dto(appt, self._service_name(appt))

    def awaiting_confirmation(self) -> list[AppointmentDTO]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(Appointment)
                .where(
                    Appointment.status == AppointmentStatus.SCHEDULED,
                    Appointment.confirmed_at.is_(None),
                    Appointment.start_time.is_not(None),
                )
                .order_by(Appointment.start_time)
            ).all()
            return [self._to_dto(row, self._service_name(row)) for row in rows]

    def cancelled_today(self, day: date | None = None) -> list[AppointmentDTO]:
        zone = ZoneInfo("Europe/Sarajevo")
        day = day or datetime.now(zone).date()
        start = datetime.combine(day, time.min, tzinfo=zone)
        end = start + timedelta(days=1)
        with self._session_factory() as session:
            rows = session.scalars(
                select(Appointment)
                .where(
                    Appointment.status.in_(
                        [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]
                    ),
                    Appointment.start_time >= start,
                    Appointment.start_time < end,
                )
                .order_by(Appointment.start_time)
            ).all()
            return [self._to_dto(row, self._service_name(row)) for row in rows]

    def pending_requests(self) -> list[RequestDTO]:
        return list_pending(self._session_factory)

    def confirm_pending(
        self, request_id: int, doctor_id: int, service_id: int, start: datetime
    ) -> None:
        confirm_request(self._session_factory, request_id, doctor_id, service_id, start)

    def reject_pending(self, request_id: int) -> None:
        reject_request(self._session_factory, request_id)

    def service_choices(self) -> list[tuple[int, str]]:
        with self._session_factory() as session:
            rows = session.scalars(select(Service).order_by(Service.naziv)).all()
            return [(row.id, row.naziv) for row in rows]

    def service_options(self) -> list[ServiceOptionDTO]:
        """Usluge sa trajanjem i bufferom (za GUI editor — trajanje se ne izmišlja)."""
        with self._session_factory() as session:
            rows = session.scalars(select(Service).order_by(Service.naziv)).all()
            return [
                ServiceOptionDTO(
                    id=row.id,
                    naziv=row.naziv,
                    trajanje_min=row.trajanje_min,
                    buffer_min=row.buffer_min,
                )
                for row in rows
            ]

    def time_off_for_week(self, week_start: date) -> list[CalendarBlockDTO]:
        zone = ZoneInfo("Europe/Sarajevo")
        start = datetime.combine(week_start, time.min, tzinfo=zone)
        end = start + timedelta(days=7)
        with self._session_factory() as session:
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

    def breaks_for_week(self, week_start: date) -> list[CalendarBlockDTO]:
        doctors = self.doctors()
        zone = ZoneInfo("Europe/Sarajevo")
        blocks: list[CalendarBlockDTO] = []
        with self._session_factory() as session:
            for doctor in doctors:
                rows = session.scalars(
                    select(WorkingHours)
                    .where(WorkingHours.doctor_id == doctor.id)
                    .order_by(WorkingHours.dan_u_sedmici, WorkingHours.od_local)
                ).all()
                by_day: dict[int, list[WorkingHours]] = {}
                for row in rows:
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
                                doctor_id=doctor.id,
                                label="PAUZA",
                            )
                        )
        return blocks

    def create_time_off(
        self,
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
        with self._session_factory() as session:
            doctor = session.get(Doctor, doctor_id)
            if doctor is None:
                raise ValueError(f"nepoznat doktor: {doctor_id}")
            self._check_timeoff_overlap(session, doctor_id, start, end)
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

    def list_time_off(self) -> list[TimeOffDTO]:
        """Aktivne i nadolazeće blokade (``do_datetime >= sada``), hronološki."""
        now = utcnow()
        with self._session_factory() as session:
            rows = session.scalars(
                select(TimeOff)
                .where(TimeOff.do_datetime >= now)
                .order_by(TimeOff.od_datetime)
            ).all()
            return [self._timeoff_dto(row) for row in rows]

    def delete_time_off(self, time_off_id: int) -> None:
        """Trajno ukloni blokadu."""
        with self._session_factory() as session:
            block = session.get(TimeOff, time_off_id)
            if block is None:
                raise ValueError(f"blokada {time_off_id} nije pronađena")
            session.delete(block)
            session.commit()

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

    # ---- postavke (doktori / usluge / radno vrijeme) ----

    def list_doctors(self) -> list[DoctorDTO]:
        """Svi doktori (aktivan + neaktivan), za postavke."""
        with self._session_factory() as session:
            doctors = session.scalars(select(Doctor).order_by(Doctor.id)).all()
            return [DoctorDTO(id=d.id, ime=d.ime, aktivan=d.aktivan) for d in doctors]

    def set_doctor_active(self, doctor_id: int, active: bool) -> DoctorDTO:
        """Aktiviraj/deaktiviraj doktora — istorija termina ostaje netaknuta."""
        with self._session_factory() as session:
            doctor = session.get(Doctor, doctor_id)
            if doctor is None:
                raise ValueError(f"nepoznat doktor: {doctor_id}")
            doctor.aktivan = active
            session.commit()
            return DoctorDTO(id=doctor.id, ime=doctor.ime, aktivan=doctor.aktivan)

    def add_service(
        self, naziv: str, trajanje_min: int, buffer_min: int
    ) -> ServiceOptionDTO:
        """Dodaj uslugu; validacija: naziv ne-prazan, trajanje>0, buffer>=0."""
        naziv = naziv.strip()
        if not naziv:
            raise ValueError("naziv usluge ne smije biti prazan")
        if trajanje_min <= 0:
            raise ValueError("trajanje usluge mora biti veće od 0 minuta")
        if buffer_min < 0:
            raise ValueError("buffer ne smije biti negativan")
        with self._session_factory() as session:
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
        self, service_id: int, naziv: str, trajanje_min: int, buffer_min: int
    ) -> ServiceOptionDTO:
        """Uredi uslugu; promjena trajanja utiče na nove termine."""
        naziv = naziv.strip()
        if not naziv:
            raise ValueError("naziv usluge ne smije biti prazan")
        if trajanje_min <= 0:
            raise ValueError("trajanje usluge mora biti veće od 0 minuta")
        if buffer_min < 0:
            raise ValueError("buffer ne smije biti negativan")
        with self._session_factory() as session:
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

    def list_working_hours(self, doctor_id: int) -> list[WorkingHoursDTO]:
        """Intervali radnog vremena doktora, sortirani po danu i početku."""
        with self._session_factory() as session:
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
        self,
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
        with self._session_factory() as session:
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
        validate_appointment_overlap(session, doctor_id, start, end, exclude_id=exclude_id)

    def _check_timeoff_overlap(
        self,
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

    @staticmethod
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
            status=appt.status,
            confirmed_at=appt.confirmed_at,
            arrived_at=appt.arrived_at,
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
