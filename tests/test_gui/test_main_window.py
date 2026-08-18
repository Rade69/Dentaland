"""Testovi glavnog prozora."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QDialog, QLabel

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


def test_dashboard_prisiljava_svijetlu_paletu(window: MainWindow) -> None:
    app = QApplication.instance()
    assert app is not None
    palette = app.palette()
    assert palette.color(QPalette.ColorRole.Window).name() == "#ffffff"
    assert palette.color(QPalette.ColorRole.Text).name() == "#10213d"


def test_sidebar_prikazuje_stvarni_dentaland_logo(window: MainWindow) -> None:
    logo = window.sidebar.findChild(QLabel, "sidebarLogo")
    assert logo is not None
    assert logo.pixmap() is not None and not logo.pixmap().isNull()


def test_navigacija_mijenja_sedmicu_i_sidebar_rutu(window: MainWindow) -> None:
    original = window.week_start
    window._move_week(1)
    assert window.week_start == original + timedelta(days=7)
    assert window.week_view.week_start == window.week_start

    window.sidebar.route_selected.emit("pacijenti")
    assert window.page_stack.currentWidget() is window._route_pages["pacijenti"]


def test_datumski_raspon_zavrsava_subotom(window: MainWindow) -> None:
    assert "17 – 22. avgust 2026" in window.range_label.text()


def test_footer_ostaje_vidljiv_na_laptop_visini(
    window: MainWindow,
    qtbot,
) -> None:
    window.resize(1536, 760)
    window.show()
    qtbot.wait(20)

    assert window.status_legend.isVisible()
    assert window.status_legend.height() >= 48
    assert "Otkazan / Nije došao" in window.status_legend.text()
    assert "No-show" not in window.status_legend.text()
    assert window.status_legend.geometry().bottom() <= window.schedule_page.rect().bottom()
    assert window.sidebar.staff.isVisible()
    assert window.sidebar.staff.geometry().bottom() <= window.sidebar.rect().bottom()


def test_paralelni_prikaz_je_vidljiv_ali_neaktivan(window: MainWindow) -> None:
    buttons = window.schedule_page.findChildren(main_window_mod.QPushButton)
    parallel = next(button for button in buttons if button.text() == "Paralelno")
    assert not parallel.isEnabled()


def test_legenda_doktora_je_poravnata_sa_desnim_panelima(
    qtbot,
    appointment_service,
    week_start,
) -> None:
    window = MainWindow(appointment_service, week_start)
    qtbot.addWidget(window)
    window.resize(1536, 760)
    window.show()
    qtbot.wait(20)

    assert window.doctor_legend.isVisible()
    assert window.doctor_legend.geometry().left() == window.dashboard_panels.geometry().left()
    assert "top: -3px" in window.styleSheet()
    assert "background-color: #ffffff" in window.styleSheet()


def test_tabovi_za_doktore_postoje(qtbot, appointment_service, week_start) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)
    assert win.doctor_tabs is not None
    labels = [win.doctor_tabs.tabText(i) for i in range(win.doctor_tabs.count())]
    assert labels == ["Svi doktori", "Ljubo", "Zorka", "Ana"]


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
