"""DENT-IMPROVE-012 — potvrđuje da aplikaciona overlap zaštita
(``validate_appointment_overlap``/``OverlapError``->409,
REF-01/DENT-IMPROVE-010) radi nepromijenjeno kad backend gađa PostgreSQL
umjesto SQLite.

Ova logika se NAMJERNO ne mijenja u ovom tasku (vidi
``src/dentaland/services/availability.py``, forbidden path) — cilj testa
je dokazati da isti kod radi na drugom SQL dijalektu, ne testirati novu
funkcionalnost.

Test se PRESKAČE (ne FAIL) ako ``DATABASE_URL_TEST`` env var nije
postavljen, tako da standardan ``pytest tests/ -q`` (bez postavljene
varijable, desktop Faza 0 / CI bez lokalne Postgres instance) ostaje
identičan baseline-u prije ovog taska. Da bi se stvarno izvršio, potrebna
je pokrenuta izolovana lokalna PostgreSQL instanca (port 5433, vidi
``.env``, NIKAD Windows ``postgresql-16`` servis na portu 5432 koji koristi
drugi projekat).

Čišćenje: svi objekti koje ovaj test kreira koriste naziv/ime obrazac
``"... Postgres ..."`` (vidi konstante ispod) — teardown ih briše po tom
obrascu umjesto praćenja pojedinačnih ID-jeva, jer je ``dentaland_test``
namijenjena isključivo testiranju i ovaj obrazac je dovoljno specifičan da
se ne poklopi ni sa čim drugim.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.main import app, get_session_factory, limiter
from dentaland.models import Appointment, AppointmentStatus, Base, Doctor, Service

DATABASE_URL_TEST = os.environ.get("DATABASE_URL_TEST")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL_TEST,
    reason=(
        "DATABASE_URL_TEST nije postavljen -- Postgres overlap test se preskace. "
        "Standardan `pytest tests/ -q` (bez DATABASE_URL_TEST) ostaje SQLite-only "
        "i identican baseline-u prije DENT-IMPROVE-012."
    ),
)

_MARKER = "Postgres Overlap Test"
_DOCTOR_NAME = f"Test Doktor {_MARKER}"
_SERVICE_NAME = f"Test Usluga {_MARKER}"
_EXISTING_PATIENT_NAME = f"Test Pacijent Postojeci {_MARKER}"
_NEW_PATIENT_NAME = f"Test Pacijent Novi {_MARKER}"


def _cleanup(session: Session) -> None:
    session.execute(
        delete(Appointment).where(
            Appointment.ime.in_([_EXISTING_PATIENT_NAME, _NEW_PATIENT_NAME])
        )
    )
    session.execute(delete(Doctor).where(Doctor.ime == _DOCTOR_NAME))
    session.execute(delete(Service).where(Service.naziv == _SERVICE_NAME))
    session.commit()


@pytest.fixture()
def pg_engine() -> Iterator[Engine]:
    assert DATABASE_URL_TEST is not None
    eng = create_engine(DATABASE_URL_TEST)
    Base.metadata.create_all(eng)  # no-op ako je alembic upgrade head vec primijenjen
    yield eng
    eng.dispose()


@pytest.fixture()
def pg_session_factory(pg_engine: Engine) -> Iterator[sessionmaker[Session]]:
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    with factory() as session:
        _cleanup(session)  # osiguraj cist pocetak i ako je prethodni run pukao prije teardown-a
    yield factory
    with factory() as session:
        _cleanup(session)


@pytest.fixture()
def client(pg_session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    # `limiter` (backend.main) je proces-singleton in-memory storage bez
    # reseta izmedju testova -- kad se cijeli `pytest tests/ -q` suite
    # pokrene, `test_backend.py::test_rate_limit_na_submit_endpointu` vec
    # namjerno potrosi kvotu za isti ("testclient") kljuc. Reset ovdje
    # izoluje ovaj test od tog dijeljenog stanja bez diranja postojeceg
    # test_backend.py (forbidden path/van scope-a ovog taska).
    limiter.reset()
    app.dependency_overrides[get_session_factory] = lambda: pg_session_factory
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def doctor_and_service(pg_session_factory: sessionmaker[Session]) -> tuple[int, int]:
    with pg_session_factory() as session:
        doctor = Doctor(ime=_DOCTOR_NAME)
        service = Service(naziv=_SERVICE_NAME, trajanje_min=30, buffer_min=0)
        session.add_all([doctor, service])
        session.commit()
        return doctor.id, service.id


def test_confirm_preklapanje_vraca_409_nad_postgres(
    client: TestClient,
    pg_session_factory: sessionmaker[Session],
    doctor_and_service: tuple[int, int],
) -> None:
    """Isti scenario kao `test_confirm_preklapanje_vraca_409`
    (tests/test_backend.py), ali sa engine-om koji gada
    DATABASE_URL_TEST (Postgres) umjesto SQLite in-memory."""
    doctor_id, service_id = doctor_and_service
    with pg_session_factory() as session:
        session.add(
            Appointment(
                doctor_id=doctor_id,
                service_id=service_id,
                ime=_EXISTING_PATIENT_NAME,
                start_time=datetime(2027, 6, 10, 9, 0, tzinfo=UTC),
                end_time=datetime(2027, 6, 10, 9, 30, tzinfo=UTC),
                status=AppointmentStatus.SCHEDULED,
            )
        )
        session.commit()

    submit = client.post(
        "/api/booking-requests",
        json={
            "ime": _NEW_PATIENT_NAME,
            "telefon": "061",
            "requested_date": "2027-06-10",
        },
    )
    assert submit.status_code == 201
    request_id = submit.json()["id"]

    response = client.post(
        f"/api/booking-requests/{request_id}/confirm",
        json={
            "doctor_id": doctor_id,
            "service_id": service_id,
            "start_time": datetime(2027, 6, 10, 9, 15, tzinfo=UTC).isoformat(),
        },
    )
    assert response.status_code == 409


def test_alembic_database_url_sa_percent_encoded_lozinkom() -> None:
    """Regresija za Codex review F1 (DENT-IMPROVE-012): `migrations/env.py`
    je prosljeđivao sirovi `DATABASE_URL` u `Config.set_main_option`, čiji
    `ConfigParser` radi interpolaciju — validan URL-encoded znak u
    kredencijalima (npr. lozinka koja sadrži `%25`) je pucao PRIJE ijednog
    pokušaja konekcije (`ValueError: invalid interpolation syntax`).

    Test ide kroz STVARAN `migrations/env.py` (subprocess `alembic current`,
    ne ručno konstruisan `Config`/engine) — percent-encoduje prvi znak
    stvarne lozinke iz `DATABASE_URL_TEST` (SQLAlchemy/psycopg2 ga ispravno
    dekoduju nazad, konekcija i dalje radi), pa dokazuje i parsing-fix i da
    se stvarno konektuje na Postgres sa takvim URL-om.
    """
    url = make_url(DATABASE_URL_TEST)
    password = url.password or ""
    assert password, "DATABASE_URL_TEST mora imati lozinku za ovaj test"
    # Ručno sastavljanje stringa (ne `url.set()` + `render_as_string`) — ovo
    # drugo bi SQLAlchemy tretiralo kao već dekodiranu lozinku i samo je
    # ponovo url-enkodiralo (`%` -> `%25`), pa bi krajnji string dekodirao
    # nazad u doslovno "%73..." umjesto stvarne lozinke.
    percent_encoded_password = f"%{ord(password[0]):02X}{password[1:]}"
    encoded_url = (
        f"{url.drivername}://{url.username}:{percent_encoded_password}"
        f"@{url.host}:{url.port}/{url.database}"
    )
    assert "%" in encoded_url
    # sanity: URL se mora dekodirati nazad u stvarnu lozinku
    assert make_url(encoded_url).password == password

    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=repo_root,
        env={**os.environ, "DATABASE_URL": encoded_url},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"alembic current je pukao sa percent-encoded DATABASE_URL:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "invalid interpolation syntax" not in result.stderr
    assert "(head)" in result.stdout
