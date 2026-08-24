"""REF-03 — arhitektonski testovi: ``booking.py`` je tanak facade.

Ovi testovi zaključavaju strukturu koju uvodi REF-03 (razbijanje
``booking.py`` po servisnim odgovornostima), nezavisno od behavioralnih
testova iz ``test_services.py``. Ključna invarijanta: poslovna logika NE
živi u facade-u, već u fokusiranim modulima.

Provjera je POZITIVNA (allowlist), ne negativna (denylist). Tijelo svake
facade metode smije sadržavati SAMO pozive ka dozvoljenim modulima
(``appointments``/``availability``/``settings``) ili ka dozvoljenim
funkcijama (``list_pending``/``confirm_request``/``reject_request``), plus
eksplicitno dozvoljeni facade-interni ``self._require_doctor``. Bilo koji
drugi poziv (raw SQL, aliasirani ``select``, ``getattr``/``__getattribute__``,
uvoz cijelog modula, ...) automatski pada — jer default je "odbij", ne
"dozvoli osim nabrojanih". Provjera je strukturna (``ast.parse``), pa ne
zavisi od teksta, formatiranja ni imena varijabli.
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


# Metode koje NISU delegacije nego facade infrastruktura — izuzete iz
# allowlist provjere. Sve ostalo (javne delegacije + bilo koje privatne)
# mora da prođe allowlist.
_FACADE_EXEMPT_METHODS = {"__init__", "from_sqlite", "set_doctor", "_require_doctor"}

# Allowlist: root imena na koje facade smije delegirati.
_FACADE_ALLOWED_MODULES = {"appointments", "availability", "settings"}
_FACADE_ALLOWED_FUNCTIONS = {"list_pending", "confirm_request", "reject_request"}
# Facade-interni poziv (state provjera, bez SQL-a) — dozvoljen po Task Contractu.
_FACADE_ALLOWED_INTERNAL = {"self._require_doctor"}
_FACADE_MODULE_OBJECTS = {
    "appointments": appointments,
    "availability": availability,
    "settings": settings,
}


def _dotted_name(expr: ast.expr) -> str | None:
    """Puni kvalifikovani naziv poziva, ili ``None`` ako nije prost Name/Attribute.

    ``getattr(...)()``, ``session.__getattribute__(...)()`` i slični dinamički
    pozivi vraćaju ``None`` (njihov ``func`` je ``ast.Call``), pa automatski
    padaju allowlist — default "odbij".
    """
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _dotted_name(expr.value)
        return f"{base}.{expr.attr}" if base is not None else None
    return None


def _is_delegation_call(call: ast.Call) -> bool:
    name = _dotted_name(call.func)
    if name is None:
        return False
    if name in _FACADE_ALLOWED_FUNCTIONS:
        return True
    parts = name.split(".")
    if len(parts) != 2 or parts[0] not in _FACADE_ALLOWED_MODULES:
        return False
    return callable(getattr(_FACADE_MODULE_OBJECTS[parts[0]], parts[1], None))


def _is_allowed_call(call: ast.Call) -> bool:
    name = _dotted_name(call.func)
    if name is None:
        return False
    if name in _FACADE_ALLOWED_INTERNAL:
        return True
    return _is_delegation_call(call)


def _is_forwarded_argument(expr: ast.expr) -> bool:
    """Delegacija prosljeđuje samo argument metode ili session factory."""
    return isinstance(expr, ast.Name) or _dotted_name(expr) == "self._session_factory"


def _assert_delegation_call_is_pure(method: ast.FunctionDef, call: ast.Call) -> None:
    assert _is_delegation_call(call), (
        f"AppointmentService.{method.name} ne delegira ka stvarnoj dozvoljenoj "
        f"funkciji: {ast.unparse(call)}"
    )
    forwarded = [*call.args, *(kw.value for kw in call.keywords)]
    bad = [ast.unparse(arg) for arg in forwarded if not _is_forwarded_argument(arg)]
    assert not bad, (
        f"AppointmentService.{method.name} ima izračunavanje/sporedni efekat "
        f"u argumentima delegacije: {bad}"
    )


def _delegation_call_from_statement(
    method: ast.FunctionDef, statement: ast.stmt
) -> ast.Call:
    if isinstance(statement, (ast.Return, ast.Expr)) and isinstance(
        statement.value, ast.Call
    ):
        call = statement.value
        _assert_delegation_call_is_pure(method, call)
        return call
    raise AssertionError(
        f"AppointmentService.{method.name} ne završava čistom delegacijom: "
        f"{ast.unparse(statement)}"
    )


def test_booking_facade_pozivi_su_samo_iz_allowlista() -> None:
    """Svaki poziv u facade metodama je dozvoljen (allowlist), default odbij."""
    for method in _appointment_service_methods():
        if method.name in _FACADE_EXEMPT_METHODS:
            continue
        bad = [
            ast.unparse(node)
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and not _is_allowed_call(node)
        ]
        assert not bad, (
            f"AppointmentService.{method.name} ima nedozvoljene pozive: {bad}"
        )


def test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik() -> None:
    """Cijelo tijelo javne metode je delegacija, uz opcioni doctor guard."""
    checked = 0
    for method in _appointment_service_methods():
        name = method.name
        if name in _FACADE_EXEMPT_METHODS:
            continue
        assert not name.startswith("_"), (
            f"AppointmentService ima neočekivanu privatnu metodu: {name}"
        )
        checked += 1

        body = method.body
        assert body, f"AppointmentService.{name} ima prazno tijelo"
        if len(body) == 2:
            guard, delegation = body
            assert isinstance(guard, ast.Assign) and len(guard.targets) == 1, (
                f"AppointmentService.{name} ima nedozvoljenu naredbu prije delegacije: "
                f"{ast.unparse(guard)}"
            )
            target = guard.targets[0]
            assert isinstance(target, ast.Name), (
                f"AppointmentService.{name} mijenja state prije delegacije: "
                f"{ast.unparse(guard)}"
            )
            assert isinstance(guard.value, ast.Call), (
                f"AppointmentService.{name} ima nedozvoljen assignment: "
                f"{ast.unparse(guard)}"
            )
            assert _dotted_name(guard.value.func) == "self._require_doctor", (
                f"AppointmentService.{name} ima nedozvoljen setup poziv: "
                f"{ast.unparse(guard)}"
            )
            assert not guard.value.args and not guard.value.keywords
            _delegation_call_from_statement(method, delegation)
        elif len(body) == 1:
            _delegation_call_from_statement(method, body[0])
        else:
            raise AssertionError(
                f"AppointmentService.{name} ima dodatne naredbe: "
                f"{[ast.unparse(stmt) for stmt in body]}"
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
