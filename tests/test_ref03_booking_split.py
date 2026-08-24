"""REF-03 — arhitektonski testovi: ``booking.py`` je tanak facade.

Ovi testovi zaključavaju strukturu koju uvodi REF-03 (razbijanje
``booking.py`` po servisnim odgovornostima), nezavisno od behavioralnih
testova iz ``test_services.py``. Ključna invarijanta: poslovna logika NE
živi u facade-u, već u fokusiranim modulima.

Provjera da facade ne sadrži SQL/data-access NIJE tekstualna (string-match)
nego strukturna — ``ast.parse`` nad ``booking.py``. Time se hvataju i raw SQL
(``text()``/``execute()``) i SQLAlchemy izrazi (``select()``/``scalar()``/
``scalars()``) bez obzira na formatiranje, naziv varijable ili prelamanje
linija.
"""

from __future__ import annotations

import ast
from pathlib import Path

from dentaland import services
from dentaland.services import AppointmentService, appointments, availability, settings

SERVICES_DIR = Path(services.__file__).parent


def _source(module_name: str) -> str:
    return (SERVICES_DIR / f"{module_name}.py").read_text(encoding="utf-8")


def _appointment_service_class() -> ast.ClassDef:
    tree = ast.parse(_source("booking"))
    return next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AppointmentService"
    )


def _appointment_service_methods() -> list[ast.FunctionDef]:
    return [n for n in _appointment_service_class().body if isinstance(n, ast.FunctionDef)]


# Data-access pozivi zabranjeni u facade metodama (osim dozvoljenog
# ``from_sqlite`` bootstrap-a). Pokriva i raw SQL (``text``/``execute``) i
# SQLAlchemy Core/ORM (``select``/``scalar``/``scalars``/``query``/``get``)
# i write operacije (``add``/``delete``/``commit``/``flush``).
_FORBIDDEN_CALL_NAMES = {"select", "text"}
_FORBIDDEN_CALL_ATTRS = {
    "execute", "scalar", "scalars", "query", "add", "delete", "commit", "flush"
}


def _is_data_access_func(func: ast.expr) -> bool:
    if isinstance(func, ast.Name):
        return func.id in _FORBIDDEN_CALL_NAMES
    if isinstance(func, ast.Attribute):
        if func.attr in _FORBIDDEN_CALL_ATTRS:
            return True
        return (
            func.attr == "get"
            and isinstance(func.value, ast.Name)
            and func.value.id == "session"
        )
    return False


def _data_access_calls(method: ast.FunctionDef) -> list[ast.Call]:
    """Vrati sve SQL/SQLAlchemy data-access pozive unutar tijela metode."""
    return [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call) and _is_data_access_func(node.func)
    ]


def test_booking_facade_ne_sadrzi_sql_data_access() -> None:
    """Nijedna facade metoda (osim ``from_sqlite``) ne smije dirati bazu."""
    for method in _appointment_service_methods():
        if method.name == "from_sqlite":
            continue
        bad = _data_access_calls(method)
        assert not bad, (
            f"AppointmentService.{method.name} sadrži data-access poziv: "
            f"{ast.unparse(bad[0])}"
        )


# Facade javne metode smiju SAMO delegirati ka fokusiranim modulima ili ka
# requests funkcijama. ``from_sqlite`` (bootstrap) i ``set_doctor`` (state
# setter) su eksplicitno izuzeti.
_DELEGATION_MODULES = {"appointments", "availability", "settings"}
_DELEGATION_FUNCTIONS = {"list_pending", "confirm_request", "reject_request"}


def _is_delegation_call(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return func.value.id in _DELEGATION_MODULES
    if isinstance(func, ast.Name):
        return func.id in _DELEGATION_FUNCTIONS
    return False


def test_booking_facade_javne_metode_su_delegacije() -> None:
    """Svaka javna facade metoda završava delegacijskim pozivom."""
    checked = 0
    for method in _appointment_service_methods():
        name = method.name
        if name.startswith("_") or name in {"from_sqlite", "set_doctor"}:
            continue
        checked += 1
        body = method.body
        assert body, f"AppointmentService.{name} ima prazno tijelo"
        last = body[-1]
        if isinstance(last, (ast.Return, ast.Expr)):
            call_node = last.value
        else:
            raise AssertionError(
                f"AppointmentService.{name} ne završava delegacijom: {ast.unparse(last)}"
            )
        assert isinstance(call_node, ast.Call) and _is_delegation_call(call_node), (
            f"AppointmentService.{name} ne delegira ka dozvoljenom modulu: "
            f"{ast.unparse(last)}"
        )
    assert checked >= 30, f"očekivano >=30 javnih delegacijskih metoda, dobijeno {checked}"


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
