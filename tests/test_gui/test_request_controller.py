"""Testovi RequestController-a (REF-07)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from desktop.controllers import request_controller as rc_mod
from desktop.controllers.request_controller import RequestController


class _Store:
    def __init__(self, *, with_doctors: bool = True) -> None:
        self._doctors = [SimpleNamespace(id=1, ime="Ljubo")] if with_doctors else []
        self._services = [(1, "Kontrola")]
        self.confirmed: list = []
        self.rejected: list = []

    def doctors(self) -> list:
        return list(self._doctors)

    def service_choices(self) -> list:
        return list(self._services)

    def confirm_pending(self, request_id, doctor_id, service_id, start) -> None:
        self.confirmed.append((request_id, doctor_id, service_id, start))

    def reject_pending(self, request_id) -> None:
        self.rejected.append(request_id)


def test_vraca_none_kad_nema_doktora() -> None:
    controller = RequestController(_Store(with_doctors=False))
    assert controller.process_pending_request(SimpleNamespace(id=1), None) is None


def test_confirm_poziva_confirm_pending(monkeypatch) -> None:
    store = _Store()
    controller = RequestController(store)
    request = SimpleNamespace(id=5)
    start = datetime(2026, 8, 18, 9, 0)

    class FakeDialog:
        def __init__(self, request, doctors, services, parent) -> None:
            pass

        def exec(self) -> int:
            return 1

        def selected_action(self) -> str:
            return "confirm"

        def values(self):
            return (1, 1, start)

    monkeypatch.setattr(rc_mod, "ProcessRequestDialog", FakeDialog)
    assert controller.process_pending_request(request, None) is True
    assert store.confirmed == [(5, 1, 1, start)]


def test_reject_poziva_reject_pending(monkeypatch) -> None:
    store = _Store()
    controller = RequestController(store)
    request = SimpleNamespace(id=7)

    class FakeDialog:
        def __init__(self, request, doctors, services, parent) -> None:
            pass

        def exec(self) -> int:
            return 1

        def selected_action(self) -> str:
            return "reject"

    monkeypatch.setattr(rc_mod, "ProcessRequestDialog", FakeDialog)
    assert controller.process_pending_request(request, None) is True
    assert store.rejected == [7]
