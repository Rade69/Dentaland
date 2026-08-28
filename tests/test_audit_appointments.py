"""Testovi audit instrumentacije CRUD funkcija termina (DENT-IMPROVE-014C).

Direktni pozivi `appointments.create_appointment`/`update_appointment`/
`cancel_appointment`/`delete_appointment` (bez `AppointmentService` facade,
isti obrazac kao `tests/test_audit.py`) — provjerava tačno JEDAN audit red
po uspješnoj operaciji, atomičnost (rollback ne upisuje ništa trajno),
`actor_user_id=NULL`, i da neuspješan pokušaj (overlap) ne upisuje audit red.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dentaland.models import AuditAction, AuditEvent, Base, Doctor, Service
from dentaland.services import appointments
from dentaland.services.availability import OverlapError


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


@pytest.fixture()
def doctor_id(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        doctor = Doctor(ime="Ljubo")
        session.add(doctor)
        session.flush()
        did = doctor.id
        session.add(Service(naziv="Kontrola", trajanje_min=30, buffer_min=0))
        session.commit()
        return did


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 27, hour, minute, tzinfo=UTC)


def _audit_rows(session_factory: sessionmaker[Session]) -> list[AuditEvent]:
    with session_factory() as session:
        return list(session.scalars(select(AuditEvent).order_by(AuditEvent.id)).all())


def test_create_appointment_upisuje_tacno_jedan_audit_red(
    session_factory: sessionmaker[Session], doctor_id: int
) -> None:
    dto = appointments.create_appointment(
        session_factory,
        doctor_id,
        "Ana Anić",
        "061111222",
        "ana@example.com",
        "Kontrola",
        "napomena koja ne smije u audit",
        _at(9),
        _at(9, 30),
    )

    rows = _audit_rows(session_factory)
    assert len(rows) == 1
    row = rows[0]
    assert row.action == AuditAction.CREATE_APPOINTMENT
    assert row.resource_type == "appointment"
    assert row.resource_id == dto.id
    assert row.actor_user_id is None


def test_update_appointment_upisuje_tacno_jedan_audit_red(
    session_factory: sessionmaker[Session], doctor_id: int
) -> None:
    dto = appointments.create_appointment(
        session_factory,
        doctor_id,
        "Ana",
        "",
        "",
        "Kontrola",
        "",
        _at(9),
        _at(9, 30),
    )

    appointments.update_appointment(
        session_factory,
        dto.id,
        patient_name="Ana Izmijenjena",
        phone="062333444",
        email="",
        doctor_id=doctor_id,
        service="Kontrola",
        note="",
        start=_at(10),
        end=_at(10, 30),
    )

    rows = _audit_rows(session_factory)
    assert len(rows) == 2  # CREATE + UPDATE
    update_row = rows[-1]
    assert update_row.action == AuditAction.UPDATE_APPOINTMENT
    assert update_row.resource_type == "appointment"
    assert update_row.resource_id == dto.id
    assert update_row.actor_user_id is None


def test_cancel_appointment_upisuje_tacno_jedan_audit_red(
    session_factory: sessionmaker[Session], doctor_id: int
) -> None:
    dto = appointments.create_appointment(
        session_factory,
        doctor_id,
        "Ana",
        "",
        "",
        "Kontrola",
        "",
        _at(9),
        _at(9, 30),
    )

    appointments.cancel_appointment(session_factory, dto.id)

    rows = _audit_rows(session_factory)
    assert len(rows) == 2  # CREATE + CANCEL
    cancel_row = rows[-1]
    assert cancel_row.action == AuditAction.CANCEL_APPOINTMENT
    assert cancel_row.resource_type == "appointment"
    assert cancel_row.resource_id == dto.id
    assert cancel_row.actor_user_id is None


def test_delete_appointment_upisuje_tacno_jedan_audit_red(
    session_factory: sessionmaker[Session], doctor_id: int
) -> None:
    dto = appointments.create_appointment(
        session_factory,
        doctor_id,
        "Ana",
        "",
        "",
        "Kontrola",
        "",
        _at(9),
        _at(9, 30),
    )

    appointments.delete_appointment(session_factory, dto.id)

    rows = _audit_rows(session_factory)
    assert len(rows) == 2  # CREATE + DELETE
    delete_row = rows[-1]
    assert delete_row.action == AuditAction.DELETE_APPOINTMENT
    assert delete_row.resource_type == "appointment"
    assert delete_row.resource_id == dto.id
    assert delete_row.actor_user_id is None


def test_create_appointment_kvar_poslije_audit_poziva_rollbackuje_oboje(
    session_factory: sessionmaker[Session],
    doctor_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex review napomena (DENT-IMPROVE-014C): docstring ovog fajla je
    tvrdio da testovi pokrivaju "atomičnost (rollback ne upisuje ništa
    trajno)", ali nijedan test nije stvarno simulirao kvar IZMEĐU audit
    poziva i commit-a — samo Codexova sopstvena adversarna proba je to
    dokazala. Ovaj test reprodukuje tačno taj scenario kao trajnu
    regresionu zaštitu: `write_audit_event` se poziva STVARNO (upisuje u
    trenutnu sesiju preko `session=`), pa se odmah nakon toga baci
    `RuntimeError` prije `create_appointment`-ovog `session.commit()`.
    Pošto je `write_audit_event(..., session=session)` dio ISTE
    transakcije, izuzetak mora povući nazad i termin i audit red."""
    from dentaland.services import audit as audit_module

    real_write_audit_event = audit_module.write_audit_event

    def _boom(*args: object, **kwargs: object) -> None:
        real_write_audit_event(*args, **kwargs)  # type: ignore[arg-type]
        raise RuntimeError("simuliran kvar izmedju audit upisa i commit-a")

    monkeypatch.setattr(appointments, "write_audit_event", _boom)

    with pytest.raises(RuntimeError):
        appointments.create_appointment(
            session_factory,
            doctor_id,
            "Ana",
            "",
            "",
            "Kontrola",
            "",
            _at(9),
            _at(9, 30),
        )

    # Ni termin ni audit red ne smiju biti trajno upisani -- cijela
    # transakcija (flush + audit add + commit) je jedna cjelina.
    with session_factory() as session:
        appointment_count = len(session.scalars(select(appointments.Appointment)).all())
    assert appointment_count == 0
    assert _audit_rows(session_factory) == []


def test_create_appointment_overlap_ne_upisuje_audit_red(
    session_factory: sessionmaker[Session], doctor_id: int
) -> None:
    appointments.create_appointment(
        session_factory,
        doctor_id,
        "Ana",
        "",
        "",
        "Kontrola",
        "",
        _at(9),
        _at(9, 30),
    )
    rows_after_first = _audit_rows(session_factory)
    assert len(rows_after_first) == 1

    with pytest.raises(OverlapError):
        appointments.create_appointment(
            session_factory,
            doctor_id,
            "Marko",
            "",
            "",
            "Kontrola",
            "",
            _at(9, 15),
            _at(9, 45),
        )

    # Neuspješan pokušaj (OverlapError prije commit-a) ne smije dodati
    # nikakav novi audit red — i dalje tačno jedan (od uspješnog create-a).
    rows_after_failed_attempt = _audit_rows(session_factory)
    assert len(rows_after_failed_attempt) == 1


def test_update_appointment_overlap_ne_upisuje_audit_red(
    session_factory: sessionmaker[Session], doctor_id: int
) -> None:
    first = appointments.create_appointment(
        session_factory,
        doctor_id,
        "Ana",
        "",
        "",
        "Kontrola",
        "",
        _at(9),
        _at(9, 30),
    )
    appointments.create_appointment(
        session_factory,
        doctor_id,
        "Marko",
        "",
        "",
        "Kontrola",
        "",
        _at(10),
        _at(10, 30),
    )
    rows_after_creates = _audit_rows(session_factory)
    assert len(rows_after_creates) == 2  # dva CREATE-a

    with pytest.raises(OverlapError):
        appointments.update_appointment(
            session_factory,
            first.id,
            patient_name="Ana",
            phone="",
            email="",
            doctor_id=doctor_id,
            service="Kontrola",
            note="",
            start=_at(10, 15),
            end=_at(10, 45),
        )

    rows_after_failed_update = _audit_rows(session_factory)
    assert len(rows_after_failed_update) == 2  # nema dodatnog UPDATE reda


def test_metadata_minimal_ne_sadrzi_licne_podatke(
    session_factory: sessionmaker[Session], doctor_id: int
) -> None:
    """Nijedna od 4 operacije ne smije upisati ime/telefon/email/napomenu
    pacijenta u `metadata_minimal` (v3.1 minimizacija)."""
    dto = appointments.create_appointment(
        session_factory,
        doctor_id,
        "Tajno Ime",
        "0619998887",
        "tajna@email.com",
        "Kontrola",
        "vrlo lična napomena o pacijentu",
        _at(9),
        _at(9, 30),
    )
    appointments.update_appointment(
        session_factory,
        dto.id,
        patient_name="Tajno Ime",
        phone="0619998887",
        email="tajna@email.com",
        doctor_id=doctor_id,
        service="Kontrola",
        note="vrlo lična napomena o pacijentu",
        start=_at(10),
        end=_at(10, 30),
    )
    appointments.cancel_appointment(session_factory, dto.id)

    forbidden = ["Tajno Ime", "0619998887", "tajna@email.com", "vrlo lična napomena"]
    for row in _audit_rows(session_factory):
        if row.metadata_minimal is None:
            continue
        decoded = json.loads(row.metadata_minimal)
        serialized = json.dumps(decoded)
        for needle in forbidden:
            assert needle not in serialized


def test_delete_appointment_metadata_minimal_bez_licnih_podataka(
    session_factory: sessionmaker[Session], doctor_id: int
) -> None:
    dto = appointments.create_appointment(
        session_factory,
        doctor_id,
        "Drugo Ime",
        "062",
        "x@example.com",
        "Kontrola",
        "napomena",
        _at(9),
        _at(9, 30),
    )
    appointments.delete_appointment(session_factory, dto.id)

    rows = _audit_rows(session_factory)
    delete_row = rows[-1]
    assert delete_row.action == AuditAction.DELETE_APPOINTMENT
    if delete_row.metadata_minimal is not None:
        serialized = delete_row.metadata_minimal
        assert "Drugo Ime" not in serialized
        assert "062" not in serialized
        assert "x@example.com" not in serialized
        assert "napomena" not in serialized
