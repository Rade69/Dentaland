"""Testovi desktop entrypointa."""

from __future__ import annotations

from pathlib import Path

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
    monkeypatch.setattr(app_module, "_resolve_db_path", lambda: Path("test-db.db"))

    assert app_module.main() == 0
    assert ("database", str(Path("test-db.db"))) in events
    assert events[-2:] == ["maximized", "exec"]


def test_resolve_db_path_koristi_cwd_kad_postoji(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dentaland.db").write_bytes(b"")
    assert app_module._resolve_db_path() == tmp_path / "dentaland.db"


def test_resolve_db_path_koristi_data_dir_kad_nema_cwd_baze(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)  # prazan tmp_path, bez dentaland.db
    monkeypatch.setenv("DENTALAND_DATA_DIR", str(tmp_path / "data"))
    assert app_module._resolve_db_path() == tmp_path / "data" / "dentaland.db"
