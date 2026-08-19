"""Testovi ProcessRequestDialog (Faza D)."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from PySide6.QtWidgets import QComboBox, QPushButton, QTimeEdit

from desktop.views.dialogs.process_request import ProcessRequestDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")

DOCTORS = [(1, "Ljubo"), (2, "Zorka")]
SERVICES = [(1, "Kontrola"), (2, "Plomba")]


def _request() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        ime="Jelena Kovač",
        telefon="061/111-222",
        email="jelena@x.com",
        requested_date=date(2026, 8, 18),
    )


def _dialog(qtbot) -> ProcessRequestDialog:
    dlg = ProcessRequestDialog(_request(), DOCTORS, SERVICES)
    qtbot.addWidget(dlg)
    return dlg


def test_dialog_ima_doktor_vrijeme_uslugu(qtbot) -> None:
    dlg = _dialog(qtbot)
    assert dlg.doctor_combo.count() == 2
    assert isinstance(dlg.time_edit, QTimeEdit)
    assert dlg.service_combo.count() == 2


def test_vrijeme_je_qtimeedit_ne_lazni_slot_dugmici(qtbot) -> None:
    dlg = _dialog(qtbot)
    assert isinstance(dlg.time_edit, QTimeEdit)
    slot_texts = {"09:00", "09:30", "10:00", "10:30"}
    buttons = [b.text() for b in dlg.findChildren(QPushButton)]
    assert not any(text in slot_texts for text in buttons)


def test_readonly_info_prikazuje_pacijenta_i_datum(qtbot) -> None:
    dlg = _dialog(qtbot)
    texts = "\n".join(label.text() for label in dlg.findChildren(type(dlg._title_label)))
    assert "Jelena Kovač" in texts
    assert "18.08.2026." in texts


def test_values_vraca_doktora_uslugu_i_vrijeme(qtbot) -> None:
    dlg = _dialog(qtbot)
    doctor_id, service_id, start = dlg.values()
    assert doctor_id == 1
    assert service_id == 1
    assert start == datetime(2026, 8, 18, 9, 0, tzinfo=SARAJEVO)


def test_selected_action_confirm(qtbot) -> None:
    dlg = _dialog(qtbot)
    confirm = next(b for b in dlg.findChildren(QPushButton) if b.text() == "Potvrdi termin")
    confirm.click()
    assert dlg.selected_action() == "confirm"


def test_selected_action_reject(qtbot) -> None:
    dlg = _dialog(qtbot)
    reject = next(b for b in dlg.findChildren(QPushButton) if b.text() == "Odbij zahtjev")
    reject.click()
    assert dlg.selected_action() == "reject"


def test_doktor_i_usluga_su_combo(qtbot) -> None:
    dlg = _dialog(qtbot)
    assert isinstance(dlg.doctor_combo, QComboBox)
    assert isinstance(dlg.service_combo, QComboBox)
