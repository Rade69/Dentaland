"""Testovi glavnog prozora."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from PySide6.QtWidgets import QDialog

from desktop.fake_data import SARAJEVO, FakeStore
from desktop.views import main_window as main_window_mod
from desktop.views.main_window import MainWindow


@pytest.fixture()
def window(qtbot, store: FakeStore, week_start: date) -> MainWindow:
    win = MainWindow(store, week_start)
    qtbot.addWidget(win)
    return win


def test_stampaj_dugme_postoji(window: MainWindow) -> None:
    assert window.print_action.text() == "Štampaj raspored"


def test_klik_na_slot_otvara_dijalog_i_dodaje_termin(qtbot, store, week_start, monkeypatch) -> None:
    class FakeDialog:
        def __init__(self, services, parent=None):
            self.services = services

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_data(self):
            return {
                "patient_name": "Ana Anić",
                "phone": "061/123-456",
                "email": "ana@example.com",
                "service": "Kontrola",
                "note": "bez napomene",
            }

    monkeypatch.setattr(main_window_mod, "AppointmentDialog", FakeDialog)
    win = MainWindow(store, week_start)
    qtbot.addWidget(win)

    start = datetime(2026, 8, 17, 8, 0, tzinfo=SARAJEVO)
    win.week_view.slot_selected.emit(start)

    appts = store.all()
    assert len(appts) == 1
    assert appts[0].patient_name == "Ana Anić"
    assert appts[0].start == start
