"""Testovi za AppointmentController (REF-04)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QDialog

from dentaland.services import OverlapError
from desktop.controllers.appointment_controller import AppointmentController
from desktop.views import main_window as main_window_mod

START = datetime(2026, 8, 17, 9, 0, tzinfo=UTC)


def _parent() -> SimpleNamespace:
    return SimpleNamespace(_doctors=[], _has_doctors=False, _current_doctor_id=None)


def _controller(store, parent=None, refreshes=None) -> AppointmentController:
    refreshes = refreshes if refreshes is not None else []
    return AppointmentController(store, parent or _parent(), lambda: refreshes.append(1))


def test_on_slot_selected_kreira_termin_i_poziva_refresh(monkeypatch) -> None:
    created: list[dict] = []
    refreshes: list[int] = []

    class FakeEditor:
        def __init__(self, doctors, service_options, start, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_data(self):
            return {
                "patient_name": "Ana",
                "phone": "",
                "email": "",
                "doctor_id": None,
                "service": "Kontrola",
                "note": "",
                "start": START,
                "duration_min": 30,
            }

        def show_error(self, message):
            pass

    store = SimpleNamespace(
        service_options=lambda: [],
        set_doctor=lambda _id: None,
        create=lambda **kw: created.append(kw),
    )
    monkeypatch.setattr(main_window_mod, "AppointmentEditorDialog", FakeEditor)

    controller = _controller(store, refreshes=refreshes)
    controller.on_slot_selected(START)

    assert len(created) == 1
    assert created[0]["patient_name"] == "Ana"
    assert created[0]["start"] == START
    assert created[0]["end"] == datetime(2026, 8, 17, 9, 30, tzinfo=UTC)
    assert refreshes == [1]


def test_on_slot_selected_retry_na_overlap(monkeypatch) -> None:
    attempts: list[dict] = []
    refreshes: list[int] = []
    errors: list[str] = []

    class FakeEditor:
        def __init__(self, doctors, service_options, start, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_data(self):
            return {
                "patient_name": "Ana",
                "phone": "",
                "email": "",
                "doctor_id": None,
                "service": "Kontrola",
                "note": "",
                "start": START,
                "duration_min": 30,
            }

        def show_error(self, message):
            errors.append(message)

    call_count = {"n": 0}

    def create(**kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OverlapError("preklapanje")
        attempts.append(kw)

    store = SimpleNamespace(
        service_options=lambda: [],
        set_doctor=lambda _id: None,
        create=create,
    )
    monkeypatch.setattr(main_window_mod, "AppointmentEditorDialog", FakeEditor)

    controller = _controller(store, refreshes=refreshes)
    controller.on_slot_selected(START)

    assert errors == ["preklapanje"]
    assert call_count["n"] == 2
    assert len(attempts) == 1
    assert refreshes == [1]


def test_handle_appointment_action_confirm(monkeypatch) -> None:
    refreshes: list[int] = []
    store = SimpleNamespace(mark_confirmed=MagicMock())
    controller = _controller(store, refreshes=refreshes)

    controller.handle_appointment_action(7, "confirm")

    store.mark_confirmed.assert_called_once_with(7)
    assert refreshes == [1]


def test_handle_appointment_action_value_error_prikazuje_warning(monkeypatch) -> None:
    refreshes: list[int] = []
    store = SimpleNamespace(
        mark_completed=MagicMock(side_effect=ValueError("terminalan")),
    )
    controller = _controller(store, refreshes=refreshes)

    with patch("desktop.controllers.appointment_controller.QMessageBox.warning") as warn:
        controller.handle_appointment_action(7, "completed")

    warn.assert_called_once()
    assert refreshes == [1]


def test_delete_appointment_poziva_store_i_refresh(monkeypatch) -> None:
    refreshes: list[int] = []

    class FakeDelete:
        def __init__(self, appt, parent=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

    store = SimpleNamespace(delete=MagicMock())
    monkeypatch.setattr(main_window_mod, "DeleteAppointmentDialog", FakeDelete)

    controller = _controller(store, refreshes=refreshes)
    controller.delete_appointment(SimpleNamespace(id=7))

    store.delete.assert_called_once_with(7)
    assert refreshes == [1]
