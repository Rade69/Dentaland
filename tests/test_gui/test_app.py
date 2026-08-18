"""Testovi desktop entrypointa."""

from __future__ import annotations

from desktop import app as app_module


def test_main_otvara_prozor_maksimizovan(monkeypatch) -> None:
    events: list[object] = []
    fake_service = object()

    class FakeApplication:
        def __init__(self, argv) -> None:
            events.append(("application", argv))

        def exec(self) -> int:
            events.append("exec")
            return 0

    class FakeAppointmentService:
        @staticmethod
        def from_sqlite(path: str):
            events.append(("database", path))
            return fake_service

    class FakeMainWindow:
        def __init__(self, service) -> None:
            assert service is fake_service

        def showMaximized(self) -> None:
            events.append("maximized")

    monkeypatch.setattr(app_module, "QApplication", FakeApplication)
    monkeypatch.setattr(app_module, "AppointmentService", FakeAppointmentService)
    monkeypatch.setattr(app_module, "MainWindow", FakeMainWindow)

    assert app_module.main() == 0
    assert ("database", "dentaland.db") in events
    assert events[-2:] == ["maximized", "exec"]
