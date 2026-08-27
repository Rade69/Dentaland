"""Testovi append-only audit log jezgra (DENT-IMPROVE-014).

Nema instrumentacije stvarnih poziva u ovom tasku (auth.py/appointments.py
netaknuti) — ovi testovi provjeravaju SAMO `write_audit_event`/`AuditEvent`
direktno, kao buduću ugovornu tačku za DENT-IMPROVE-014B/014C.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dentaland.models import AuditAction, AuditEvent, Base, User, UserRole
from dentaland.services.audit import write_audit_event
from dentaland.services.auth import hash_password


@pytest.fixture()
def engine() -> Engine:
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def _make_user(session: Session, username: str = "recepcija1") -> int:
    user = User(
        username=username,
        password_hash=hash_password("nebitna-lozinka-123"),
        role=UserRole.RECEPTION,
    )
    session.add(user)
    session.flush()
    return user.id


def test_write_audit_event_upisuje_sva_polja(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        user_id = _make_user(session)
        session.commit()

    write_audit_event(
        session_factory,
        AuditAction.LOGIN_SUCCESS,
        actor_user_id=user_id,
        resource_type="user",
        resource_id=user_id,
        request_id="req-123",
        source_ip="203.0.113.7",
        metadata={"note": "test"},
    )

    with session_factory() as session:
        rows = session.scalars(select(AuditEvent)).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.actor_user_id == user_id
        assert row.action == AuditAction.LOGIN_SUCCESS
        assert row.resource_type == "user"
        assert row.resource_id == user_id
        assert row.occurred_at is not None
        assert row.occurred_at.tzinfo is not None
        assert row.request_id == "req-123"
        assert row.source_ip == "203.0.113.7"
        assert json.loads(row.metadata_minimal) == {"note": "test"}


def test_write_audit_event_sva_nullable_polja_prihvataju_none(
    session_factory: sessionmaker[Session],
) -> None:
    write_audit_event(session_factory, AuditAction.LOGIN_FAILURE)

    with session_factory() as session:
        rows = session.scalars(select(AuditEvent)).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.actor_user_id is None
        assert row.action == AuditAction.LOGIN_FAILURE
        assert row.resource_type is None
        assert row.resource_id is None
        assert row.request_id is None
        assert row.source_ip is None
        assert row.metadata_minimal is None


@pytest.mark.parametrize(
    "action",
    [
        AuditAction.LOGIN_SUCCESS,
        AuditAction.LOGIN_FAILURE,
        AuditAction.CREATE_APPOINTMENT,
        AuditAction.UPDATE_APPOINTMENT,
        AuditAction.CANCEL_APPOINTMENT,
        AuditAction.DELETE_APPOINTMENT,
        AuditAction.CHANGE_ROLE,
    ],
)
def test_write_audit_event_sve_akcije_upisive(
    session_factory: sessionmaker[Session], action: AuditAction
) -> None:
    write_audit_event(session_factory, action)

    with session_factory() as session:
        rows = session.scalars(select(AuditEvent).where(AuditEvent.action == action)).all()
        assert len(rows) == 1


def test_uzastopni_pozivi_ne_mijenjaju_prethodne_redove(
    session_factory: sessionmaker[Session],
) -> None:
    """Append-only ponašanje na nivou funkcije — svaki poziv dodaje novi
    red, nijedan poziv ne mijenja/briše prethodne."""
    write_audit_event(
        session_factory,
        AuditAction.LOGIN_SUCCESS,
        resource_type="user",
        resource_id=1,
    )
    write_audit_event(
        session_factory,
        AuditAction.CREATE_APPOINTMENT,
        resource_type="appointment",
        resource_id=42,
    )
    write_audit_event(
        session_factory,
        AuditAction.CANCEL_APPOINTMENT,
        resource_type="appointment",
        resource_id=42,
    )

    with session_factory() as session:
        rows = session.scalars(select(AuditEvent).order_by(AuditEvent.id)).all()
        assert len(rows) == 3
        assert rows[0].action == AuditAction.LOGIN_SUCCESS
        assert rows[0].resource_id == 1
        assert rows[1].action == AuditAction.CREATE_APPOINTMENT
        assert rows[1].resource_id == 42
        assert rows[2].action == AuditAction.CANCEL_APPOINTMENT
        assert rows[2].resource_id == 42
        # Prvi red ostaje netaknut nakon narednih poziva.
        assert rows[0].resource_type == "user"


def test_write_audit_event_sa_postojecom_sesijom_ne_commituje(
    session_factory: sessionmaker[Session],
) -> None:
    """Kad je `session` prosljeđena, `write_audit_event` NE commit-uje —
    pozivalac kontroliše commit granicu (DENT-IMPROVE-014C atomičnost sa
    izmjenom termina)."""
    with session_factory() as session:
        write_audit_event(
            session_factory,
            AuditAction.CREATE_APPOINTMENT,
            resource_type="appointment",
            resource_id=7,
            session=session,
        )
        # Prije commit-a, u DRUGOJ sesiji red ne smije biti vidljiv.
        with session_factory() as other_session:
            assert other_session.scalars(select(AuditEvent)).all() == []
        session.commit()

    with session_factory() as session:
        rows = session.scalars(select(AuditEvent)).all()
        assert len(rows) == 1
        assert rows[0].resource_id == 7


def test_write_audit_event_sa_postojecom_sesijom_rollback_ne_upisuje(
    session_factory: sessionmaker[Session],
) -> None:
    """Atomičnost: ako pozivalac rollback-uje sesiju (npr. jer je prateća
    izmjena termina propala), audit red se ne smije trajno upisati."""
    with session_factory() as session:
        write_audit_event(
            session_factory,
            AuditAction.DELETE_APPOINTMENT,
            resource_type="appointment",
            resource_id=99,
            session=session,
        )
        session.rollback()

    with session_factory() as session:
        rows = session.scalars(select(AuditEvent)).all()
        assert rows == []


def test_metadata_minimal_ne_validira_niti_sanitizuje_sadrzaj(
    session_factory: sessionmaker[Session],
) -> None:
    """Po dizajnu (dokumentovano u docstringu), `write_audit_event` ne
    provjerava sadržaj `metadata` — odgovornost je isključivo na
    pozivaocu. Ovaj test dokumentuje/potvrđuje to ponašanje (ne da je
    poželjno ovdje ubaciti tajnu u produkcijskom pozivu)."""
    write_audit_event(
        session_factory,
        AuditAction.LOGIN_FAILURE,
        metadata={"cak_i_ovo_prolazi": "nije-posao-ove-funkcije-da-filtrira"},
    )

    with session_factory() as session:
        row = session.scalars(select(AuditEvent)).one()
        assert json.loads(row.metadata_minimal) == {
            "cak_i_ovo_prolazi": "nije-posao-ove-funkcije-da-filtrira"
        }


def test_servisni_sloj_nema_update_delete_funkciju_za_audit() -> None:
    """Provjera da servisni sloj STVARNO ne izlaže mutacioni API (append-only
    po disciplini, ne po DB trigeru) — reviewer napomena iz task kontrakta."""
    import dentaland.services.audit as audit_module

    public_names = [name for name in dir(audit_module) if not name.startswith("_")]
    for name in public_names:
        assert "update" not in name.lower()
        assert "delete" not in name.lower()
