"""REF-00 — characterization baseline za DVIJE odvojene ``OverlapError`` klase.

Dokumentuje trenutno stanje (24.8.2026) koje REF-01 mora svjesno zadržati
ili promijeniti, ne slučajno slomiti:

- ``booking.OverlapError`` (``src/dentaland/services/booking.py:135``) —
  re-eksport kroz ``dentaland.services``; hvataju je desktop view-ovi
  ``main_window``, ``day_view``, ``week_view``, ``blockout_panel``.
- ``requests.OverlapError`` (``src/dentaland/services/requests.py:30``) —
  hvataju je ``backend/main.py`` i ``desktop/views/requests_panel.py``.
"""

from __future__ import annotations

import os

# Isti mehanizam kao tests/test_gui/conftest.py — omogućava bezbedan import
# Qt modula (desktop view-ova) u testovima koji provjeravaju catch-mapiranje.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from dentaland.models import Appointment, AppointmentStatus, Base, Doctor, Service
from dentaland.services import AppointmentService
from dentaland.services import OverlapError as ServicesOverlapError
from dentaland.services.booking import OverlapError as BookingOverlapError
from dentaland.services.requests import (
    OverlapError as RequestsOverlapError,
)
from dentaland.services.requests import (
    confirm_request,
    create_request,
)


def test_dve_klase_istog_imena_su_razlicite() -> None:
    assert BookingOverlapError is not RequestsOverlapError


def test_services_reexport_je_booking_klasa() -> None:
    assert ServicesOverlapError is BookingOverlapError
    assert ServicesOverlapError is not RequestsOverlapError


def test_backend_main_hvata_requests_klasu() -> None:
    import backend.main as backend_main

    assert backend_main.OverlapError is RequestsOverlapError
    assert backend_main.OverlapError is not BookingOverlapError


def test_desktop_main_window_hvata_booking_klasu() -> None:
    from desktop.views import main_window

    assert main_window.OverlapError is BookingOverlapError


def test_desktop_day_view_hvata_booking_klasu() -> None:
    from desktop.views import day_view

    assert day_view.OverlapError is BookingOverlapError


def test_desktop_week_view_hvata_booking_klasu() -> None:
    from desktop.views import week_view

    assert week_view.OverlapError is BookingOverlapError


def test_desktop_blockout_panel_hvata_booking_klasu() -> None:
    from desktop.views import blockout_panel

    assert blockout_panel.OverlapError is BookingOverlapError


def test_desktop_requests_panel_hvata_requests_klasu() -> None:
    from desktop.views import requests_panel

    assert requests_panel.OverlapError is RequestsOverlapError


# --- Behavior: koja klasa se stvarno baca sa kojeg poziva ---


def test_service_create_baca_booking_klasu(tmp_path) -> None:
    svc = AppointmentService.from_sqlite(str(tmp_path / "dentaland.db"))
    start = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
    end = start + timedelta(minutes=30)
    service_name = svc.services()[0]
    svc.create("Postojeci", "", "", service_name, "", start, end)

    with pytest.raises(BookingOverlapError) as excinfo:
        svc.create("Novi", "", "", service_name, "", start, end)

    assert type(excinfo.value) is BookingOverlapError
    assert type(excinfo.value) is not RequestsOverlapError


def test_confirm_request_baca_requests_klasu(tmp_path) -> None:
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
    sf = sessionmaker(bind=eng, expire_on_commit=False)
    with sf() as session:
        doctor = Doctor(ime="Ljubo")
        service = Service(naziv="Kontrola", trajanje_min=30, buffer_min=0)
        session.add_all([doctor, service])
        session.commit()
        doctor_id = doctor.id
        service_id = service.id
        session.add(
            Appointment(
                doctor_id=doctor_id,
                service_id=service_id,
                ime="Postojeci",
                start_time=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
                end_time=datetime(2026, 8, 20, 9, 30, tzinfo=UTC),
                status=AppointmentStatus.SCHEDULED,
            )
        )
        session.commit()

    dto = create_request(sf, "Ana", "061", "", date(2026, 8, 20))
    with pytest.raises(RequestsOverlapError) as excinfo:
        confirm_request(
            sf,
            dto.id,
            doctor_id,
            service_id,
            datetime(2026, 8, 20, 9, 15, tzinfo=UTC),
        )

    assert type(excinfo.value) is RequestsOverlapError
    assert type(excinfo.value) is not BookingOverlapError
    eng.dispose()
