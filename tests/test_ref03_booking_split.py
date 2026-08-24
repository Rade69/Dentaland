"""REF-03 — arhitektonski testovi: ``booking.py`` je tanak facade.

Ovi testovi zaključavaju strukturu koju uvodi REF-03 (razbijanje
``booking.py`` po servisnim odgovornostima), nezavisno od behavioralnih
testova iz ``test_services.py``. Ključna invarijanta: poslovna logika NE
živi u facade-u, već u fokusiranim modulima.
"""

from __future__ import annotations

from pathlib import Path

from dentaland import services
from dentaland.services import AppointmentService, appointments, availability, settings

SERVICES_DIR = Path(services.__file__).parent


def _source(module_name: str) -> str:
    return (SERVICES_DIR / f"{module_name}.py").read_text(encoding="utf-8")


def test_booking_facade_ne_sadrzi_appointment_crud_sql() -> None:
    """Facade delegira — ne smije držati SQL za Appointment CRUD/status."""
    src = _source("booking")
    assert "select(Appointment)" not in src
    assert "session.get(Appointment" not in src
    assert "Appointment(" not in src


def test_booking_facade_ne_implementira_overlap() -> None:
    """Overlap invariant živi u availability.py, ne u facade-u."""
    src = _source("booking")
    assert "validate_appointment_overlap" not in src
    assert "Appointment.start_time < end" not in src
    assert "Appointment.end_time > start" not in src


def test_appointment_crud_odvojen_od_settings() -> None:
    """CRUD/status funkcije žive u appointments.py, settings u settings.py."""
    appointments_src = _source("appointments")
    settings_src = _source("settings")

    # Appointment CRUD/status — u appointments.py, NE u settings.py.
    assert "def create_appointment(" in appointments_src
    assert "def mark_completed(" in appointments_src
    assert "def create_appointment(" not in settings_src
    assert "def mark_completed(" not in settings_src

    # Settings administracija — u settings.py, NE u appointments.py.
    assert "def set_doctor_active(" in settings_src
    assert "def add_service(" in settings_src
    assert "def set_doctor_active(" not in appointments_src
    assert "def add_service(" not in appointments_src


def test_moduli_izlazu_ocekivane_funkcije() -> None:
    assert callable(appointments.create_appointment)
    assert callable(appointments.mark_completed)
    assert callable(settings.set_doctor_active)
    assert callable(settings.add_service)
    assert callable(availability.time_off_for_week)
    assert callable(availability.create_time_off)


def test_appointments_koristi_dijeljenu_overlap_provjeru() -> None:
    """appointments.py ne duplira overlap SQL — koristi shared invariant."""
    src = _source("appointments")
    assert "from dentaland.services.availability import validate_appointment_overlap" in src
    assert "def validate_appointment_overlap" not in src


def test_facade_metoda_delegira(monkeypatch) -> None:
    """``AppointmentService.mark_arrived`` je jednoredna delegacija."""
    calls: list[tuple[object, int]] = []

    def fake_mark_arrived(session_factory: object, appt_id: int) -> str:
        calls.append((session_factory, appt_id))
        return "sentinel"

    monkeypatch.setattr(appointments, "mark_arrived", fake_mark_arrived)
    session_factory = lambda: None  # noqa: E731 — dummy, ne poziva se u testu
    service = AppointmentService(session_factory, doctor_id=1)

    assert service.mark_arrived(42) == "sentinel"
    assert calls == [(session_factory, 42)]
