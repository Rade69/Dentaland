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


def test_tabovi_za_doktore_postoje(qtbot, appointment_service, week_start) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)
    assert win.doctor_tabs is not None
    labels = [win.doctor_tabs.tabText(i) for i in range(win.doctor_tabs.count())]
    assert labels == ["Svi doktori", "Dr Ljubo", "Dr Zorka", "Dr Ana"]


def test_unos_u_svi_doktori_trazi_doktora(
    qtbot, appointment_service, week_start, monkeypatch
) -> None:
    class FakeDialog:
        def __init__(self, services, parent=None):
            self.services = services

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_data(self):
            return {
                "patient_name": "Ana Anić",
                "phone": "",
                "email": "",
                "service": "Kontrola",
                "note": "",
            }

    class FakeInputDialog:
        @staticmethod
        def getItem(parent, title, label, items, current, editable):
            assert "Zorka" in items
            return "Zorka", True

    monkeypatch.setattr(main_window_mod, "AppointmentDialog", FakeDialog)
    monkeypatch.setattr(main_window_mod, "QInputDialog", FakeInputDialog)

    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)
    assert win._current_doctor_id is None  # podrazumijevano "Svi doktori"

    start = datetime(2026, 8, 17, 8, 0, tzinfo=SARAJEVO)
    win.week_view.slot_selected.emit(start)

    created = appointment_service.all_combined()
    assert len(created) == 1
    assert created[0].doctor_name == "Zorka"


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
