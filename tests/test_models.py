"""Testovi za SQLAlchemy modele Faze 0 (DENT-001)."""

from __future__ import annotations

from datetime import UTC, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from dentaland.models import (
    Appointment,
    AppointmentStatus,
    Base,
    Doctor,
    Service,
    TimeOff,
    TZDateTime,
    WorkingHours,
)


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
def session(engine: Engine):
    with Session(engine) as sess:
        yield sess


def _make_doctor(session: Session, ime: str = "Ljubo") -> Doctor:
    doctor = Doctor(ime=ime)
    session.add(doctor)
    session.flush()
    return doctor


def _make_service(session: Session) -> Service:
    service = Service(naziv="Kontrola", trajanje_min=30, buffer_min=10)
    session.add(service)
    session.flush()
    return service


def test_sve_tabele_su_kreirane(engine: Engine) -> None:
    table_names = set(inspect(engine).get_table_names())
    # "users"/"sessions" dodani u DENT-IMPROVE-013 (autentifikacija + RBAC).
    # "audit_events" dodan u DENT-IMPROVE-014 (append-only audit log, jezgro).
    assert table_names == {
        "doctors",
        "services",
        "working_hours",
        "time_off",
        "appointments",
        "users",
        "sessions",
        "audit_events",
    }


def test_alembic_migracija_ima_status_constraint_i_manual_override_default(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")

    migrated_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    migrated_inspector = inspect(migrated_engine)
    checks = migrated_inspector.get_check_constraints("appointments")
    columns = {column["name"]: column for column in migrated_inspector.get_columns("appointments")}

    assert any(
        "status" in (check["sqltext"] or "")
        and "SCHEDULED" in (check["sqltext"] or "")
        and "NO_SHOW" in (check["sqltext"] or "")
        for check in checks
    )
    assert columns["is_manual_override"]["default"] in {"0", "false", "FALSE"}

    command.downgrade(config, "base")
    remaining_tables = set(inspect(migrated_engine).get_table_names())
    assert remaining_tables <= {"alembic_version"}
    migrated_engine.dispose()


def test_fk_working_hours_time_off_appointments_na_doctors(engine: Engine) -> None:
    insp = inspect(engine)
    for table in ("working_hours", "time_off", "appointments"):
        fks = insp.get_foreign_keys(table)
        targets = {(fk["constrained_columns"][0], fk["referred_table"]) for fk in fks}
        assert ("doctor_id", "doctors") in targets, f"{table} nema FK na doctors"


def test_fk_appointments_na_services(engine: Engine) -> None:
    fks = inspect(engine).get_foreign_keys("appointments")
    targets = {(fk["constrained_columns"][0], fk["referred_table"]) for fk in fks}
    assert ("service_id", "services") in targets


def test_working_hours_ima_eksplicitno_timezone_polje(session: Session) -> None:
    doctor = _make_doctor(session)
    wh = WorkingHours(
        doctor_id=doctor.id,
        dan_u_sedmici=1,
        od_local=time(8, 0),
        do_local=time(16, 0),
        timezone="Europe/Sarajevo",
    )
    session.add(wh)
    session.flush()
    assert wh.timezone == "Europe/Sarajevo"


def test_time_off_je_timezone_aware(session: Session) -> None:
    doctor = _make_doctor(session)
    time_off = TimeOff(
        doctor_id=doctor.id,
        od_datetime=datetime(2026, 8, 20, 8, 0, tzinfo=UTC),
        do_datetime=datetime(2026, 8, 20, 16, 0, tzinfo=UTC),
        razlog="Godišnji",
    )
    session.add(time_off)
    session.flush()
    assert time_off.od_datetime.utcoffset() is not None
    assert time_off.do_datetime.utcoffset() is not None


def test_tzdatetime_odbacuje_naivan_datetime() -> None:
    naive = datetime(2026, 8, 20, 10, 0)
    with pytest.raises(ValueError):
        TZDateTime().process_bind_param(naive, None)


def test_tzdatetime_prihvata_aware_datetime() -> None:
    aware = datetime(2026, 8, 20, 10, 0, tzinfo=ZoneInfo("Europe/Sarajevo"))
    result = TZDateTime().process_bind_param(aware, None)
    assert result is not None
    assert result.utcoffset() is not None
    assert result.tzinfo == UTC


def test_appointment_roundtrip_je_timezone_aware(session: Session) -> None:
    doctor = _make_doctor(session)
    service = _make_service(session)
    start = datetime(2026, 8, 20, 10, 0, tzinfo=ZoneInfo("Europe/Sarajevo"))
    end = datetime(2026, 8, 20, 10, 30, tzinfo=ZoneInfo("Europe/Sarajevo"))

    appt = Appointment(
        doctor_id=doctor.id,
        service_id=service.id,
        ime="Pacijent",
        start_time=start,
        end_time=end,
    )
    session.add(appt)
    session.flush()

    assert appt.start_time.utcoffset() is not None
    assert appt.end_time.utcoffset() is not None


def test_appointment_odbacuje_naivan_start_time(session: Session) -> None:
    doctor = _make_doctor(session)
    service = _make_service(session)
    appt = Appointment(
        doctor_id=doctor.id,
        service_id=service.id,
        ime="Pacijent",
        start_time=datetime(2026, 8, 20, 10, 0),
        end_time=datetime(2026, 8, 20, 10, 30, tzinfo=UTC),
    )
    session.add(appt)
    with pytest.raises(StatementError, match="naivan datetime"):
        session.flush()
    session.rollback()


def test_status_je_enum_i_default_scheduled(session: Session) -> None:
    doctor = _make_doctor(session)
    service = _make_service(session)
    appt = Appointment(
        doctor_id=doctor.id,
        service_id=service.id,
        ime="Pacijent",
        start_time=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 8, 20, 10, 30, tzinfo=UTC),
    )
    session.add(appt)
    session.flush()

    assert appt.status == AppointmentStatus.SCHEDULED


def test_status_odbacuje_nevalidnu_vrijednost(session: Session) -> None:
    doctor = _make_doctor(session)
    service = _make_service(session)
    appt = Appointment(
        doctor_id=doctor.id,
        service_id=service.id,
        ime="Pacijent",
        start_time=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 8, 20, 10, 30, tzinfo=UTC),
        status="NEPOSTOJECI",
    )
    session.add(appt)
    with pytest.raises(StatementError, match="not among the defined enum values"):
        session.flush()
    session.rollback()


def test_is_manual_override_default_false(session: Session) -> None:
    doctor = _make_doctor(session)
    service = _make_service(session)
    appt = Appointment(
        doctor_id=doctor.id,
        service_id=service.id,
        ime="Pacijent",
        start_time=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 8, 20, 10, 30, tzinfo=UTC),
    )
    session.add(appt)
    session.flush()
    assert appt.is_manual_override is False


def test_confirmed_arrived_at_default_none(session: Session) -> None:
    doctor = _make_doctor(session)
    service = _make_service(session)
    appt = Appointment(
        doctor_id=doctor.id,
        service_id=service.id,
        ime="Pacijent",
        start_time=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 8, 20, 10, 30, tzinfo=UTC),
    )
    session.add(appt)
    session.flush()
    assert appt.confirmed_at is None
    assert appt.arrived_at is None


def test_confirmed_arrived_at_prihvataju_aware_datetime(session: Session) -> None:
    doctor = _make_doctor(session)
    service = _make_service(session)
    appt = Appointment(
        doctor_id=doctor.id,
        service_id=service.id,
        ime="Pacijent",
        start_time=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 8, 20, 10, 30, tzinfo=UTC),
        confirmed_at=datetime(2026, 8, 18, 9, 0, tzinfo=ZoneInfo("Europe/Sarajevo")),
        arrived_at=datetime(2026, 8, 20, 9, 55, tzinfo=UTC),
    )
    session.add(appt)
    session.flush()
    assert appt.confirmed_at.utcoffset() is not None
    assert appt.arrived_at.utcoffset() is not None


def test_alembic_migracija_dodaje_confirmed_arrived_at(tmp_path: Path) -> None:
    database_path = tmp_path / "migration_dent012.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")

    migrated_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    columns = {
        column["name"]: column
        for column in inspect(migrated_engine).get_columns("appointments")
    }
    assert columns["confirmed_at"]["nullable"] is True
    assert columns["arrived_at"]["nullable"] is True

    command.downgrade(config, "base")
    remaining_tables = set(inspect(migrated_engine).get_table_names())
    assert remaining_tables <= {"alembic_version"}
    migrated_engine.dispose()


def test_migracija_cuva_postojece_termine_pri_upgrade_i_downgrade(tmp_path: Path) -> None:
    """Regresija zatražena u DENT-012 review-u (Codex, 17.8.2026).

    Prazna baza (test iznad) ne dokazuje da batch-mode recreate ne gubi
    POSTOJEĆE redove. Ovdje: upgrade do revizije PRIJE DENT-012, upis
    stvarnog termina, pa upgrade na head (mora dobiti NULL u oba nova
    polja), pa downgrade nazad (termin i status moraju ostati netaknuti).
    """
    database_path = tmp_path / "migration_dent012_data.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "b2c3d4e5f6a7")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO doctors (id, ime, aktivan) VALUES (1, 'Ljubo', 1)"))
        conn.execute(
            text(
                "INSERT INTO services (id, naziv, trajanje_min, buffer_min) "
                "VALUES (1, 'Kontrola', 30, 0)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO appointments "
                "(id, doctor_id, service_id, ime, telefon, email, napomena, requested_date, "
                "start_time, end_time, status, is_manual_override, created_at, updated_at) "
                "VALUES (1, 1, 1, 'Postojeći Pacijent', '061111222', NULL, NULL, NULL, "
                "'2026-08-20 10:00:00', '2026-08-20 10:30:00', 'SCHEDULED', 0, "
                "'2026-08-17 00:00:00', '2026-08-17 00:00:00')"
            )
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT confirmed_at, arrived_at, status, ime FROM appointments WHERE id=1")
        ).one()
        assert row.confirmed_at is None
        assert row.arrived_at is None
        assert row.status == "SCHEDULED"
        assert row.ime == "Postojeći Pacijent"
    engine.dispose()

    command.downgrade(config, "b2c3d4e5f6a7")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.connect() as conn:
        row = conn.execute(text("SELECT status, ime FROM appointments WHERE id=1")).one()
        assert row.status == "SCHEDULED"
        assert row.ime == "Postojeći Pacijent"
    columns = {c["name"] for c in inspect(engine).get_columns("appointments")}
    assert "confirmed_at" not in columns
    assert "arrived_at" not in columns
    engine.dispose()


def test_relacije_doctor_service_appointment(session: Session) -> None:
    doctor = _make_doctor(session)
    service = _make_service(session)
    appt = Appointment(
        doctor_id=doctor.id,
        service_id=service.id,
        ime="Pacijent",
        start_time=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 8, 20, 10, 30, tzinfo=UTC),
    )
    session.add(appt)
    session.flush()

    assert appt in doctor.appointments
    assert appt in service.appointments
    assert appt.doctor is doctor
    assert appt.service is service
