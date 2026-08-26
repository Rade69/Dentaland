"""GUI testovi za postavke (DENT-IMPROVE-005)."""

from __future__ import annotations

from datetime import time
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QCheckBox, QDialog, QPushButton, QTableWidget, QTabWidget

from desktop.controllers.settings_controller import SettingsController
from desktop.views import settings_panel as settings_panel_mod
from desktop.views.settings_panel import IntervalDialog, ServiceDialog, SettingsPanel


def _make_panel(qtbot, appointment_service) -> SettingsPanel:
    panel = SettingsPanel(appointment_service)
    qtbot.addWidget(panel)
    return panel


def test_panel_ima_tri_taba(qtbot, appointment_service) -> None:
    panel = _make_panel(qtbot, appointment_service)
    tabs = panel.findChild(QTabWidget)
    assert tabs is not None
    assert tabs.count() == 3
    assert [tabs.tabText(i) for i in range(3)] == ["Doktori", "Usluge", "Radno vrijeme"]


def test_doktori_prikazani_kao_checkbox(qtbot, appointment_service) -> None:
    panel = _make_panel(qtbot, appointment_service)
    checkboxes = panel.findChildren(QCheckBox)
    names = [cb.text() for cb in checkboxes]
    assert "Ljubo" in names
    assert "Zorka" in names
    assert "Ana" in names
    # Seed doktori su aktivni po defaultu.
    assert all(cb.isChecked() for cb in checkboxes)


def test_toggle_doktora_deaktivira(qtbot, appointment_service) -> None:
    panel = _make_panel(qtbot, appointment_service)
    ljubo = next(cb for cb in panel.findChildren(QCheckBox) if cb.text() == "Ljubo")
    ljubo.setChecked(False)

    doctors = {d.ime: d for d in appointment_service.list_doctors()}
    assert doctors["Ljubo"].aktivan is False
    assert doctors["Zorka"].aktivan is True


def test_usluge_u_tabeli(qtbot, appointment_service) -> None:
    panel = _make_panel(qtbot, appointment_service)
    table = panel.findChild(QTableWidget)
    assert table is not None
    assert table.rowCount() >= 5  # seed usluge
    names = [table.item(row, 0).text() for row in range(table.rowCount())]
    assert "Kontrola" in names
    assert "Plomba" in names


def test_service_dialog_ima_odustani_i_sacuvaj(qtbot) -> None:
    dialog = ServiceDialog()
    qtbot.addWidget(dialog)
    texts = {button.text() for button in dialog.findChildren(QPushButton)}
    assert "Odustani" in texts
    assert "Sačuvaj" in texts
    assert "OK" not in texts
    assert "Cancel" not in texts


def test_interval_dialog_ima_odustani_i_sacuvaj(qtbot) -> None:
    dialog = IntervalDialog()
    qtbot.addWidget(dialog)
    texts = {button.text() for button in dialog.findChildren(QPushButton)}
    assert "Odustani" in texts
    assert "Sačuvaj" in texts
    assert "OK" not in texts
    assert "Cancel" not in texts


def test_service_dialog_values_vraca_formu(qtbot) -> None:
    dialog = ServiceDialog(naziv="Plomba", trajanje=60, buffer=15)
    qtbot.addWidget(dialog)
    assert dialog.values() == ("Plomba", 60, 15)
    dialog.trajanje_spin.setValue(90)
    dialog.buffer_spin.setValue(20)
    assert dialog.values() == ("Plomba", 90, 20)


def test_service_dialog_sacuvaj_acceptuje(qtbot) -> None:
    dialog = ServiceDialog()
    qtbot.addWidget(dialog)
    sacuvaj = next(
        button for button in dialog.findChildren(QPushButton) if button.text() == "Sačuvaj"
    )
    sacuvaj.click()
    assert dialog.result() != 0  # QDialog.Rejected == 0; accept() je pozvan


def test_service_dialog_odustani_odbija(qtbot) -> None:
    dialog = ServiceDialog()
    qtbot.addWidget(dialog)
    odustani = next(
        button for button in dialog.findChildren(QPushButton) if button.text() == "Odustani"
    )
    odustani.click()
    assert dialog.result() == 0  # QDialog.Rejected


def test_interval_dialog_values_vraca_formu(qtbot) -> None:
    dialog = IntervalDialog()
    qtbot.addWidget(dialog)
    od_local, do_local = dialog.values()
    assert (od_local.hour, od_local.minute) == (8, 0)
    assert (do_local.hour, do_local.minute) == (9, 0)


# --- REF-12: delegacija ide SettingsController-u, ne direktno store-u ---


class SpyStore:
    """Read metode rade; mutacijske bacaju AssertionError (direktan poziv = regresija)."""

    def __init__(self) -> None:
        self._doctor = SimpleNamespace(id=1, ime="Ljubo", aktivan=True)
        self._service = SimpleNamespace(id=1, naziv="Kontrola", trajanje_min=30, buffer_min=10)

    def list_doctors(self) -> list:
        return [self._doctor]

    def doctors(self) -> list:
        return [SimpleNamespace(id=1, ime="Ljubo")]

    def service_options(self) -> list:
        return [self._service]

    def list_working_hours(self, doctor_id: int) -> list:
        return []

    def set_doctor_active(self, *args) -> None:
        raise AssertionError("direktan store.set_doctor_active")

    def add_service(self, *args) -> None:
        raise AssertionError("direktan store.add_service")

    def update_service(self, *args) -> None:
        raise AssertionError("direktan store.update_service")

    def set_working_hours(self, *args) -> None:
        raise AssertionError("direktan store.set_working_hours")


class SpySettingsController:
    def __init__(self) -> None:
        self.calls: list = []

    def set_doctor_active(self, doctor_id, active) -> None:
        self.calls.append(("set_doctor_active", doctor_id, active))

    def add_service(self, naziv, trajanje_min, buffer_min) -> None:
        self.calls.append(("add_service", naziv, trajanje_min, buffer_min))

    def update_service(self, service_id, naziv, trajanje_min, buffer_min) -> None:
        self.calls.append(("update_service", service_id, naziv, trajanje_min, buffer_min))

    def set_working_hours(self, doctor_id, dan, intervals) -> None:
        self.calls.append(("set_working_hours", doctor_id, dan, intervals))


def test_toggle_doktora_delegira_controlleru(qtbot) -> None:
    store = SpyStore()
    panel = SettingsPanel(store)
    qtbot.addWidget(panel)

    spy = SpySettingsController()
    panel._settings_controller = spy

    ljubo = next(cb for cb in panel.findChildren(QCheckBox) if cb.text() == "Ljubo")
    ljubo.setChecked(False)

    assert spy.calls == [("set_doctor_active", 1, False)]


def test_add_service_delegira_controlleru(qtbot, monkeypatch) -> None:
    store = SpyStore()
    panel = SettingsPanel(store)
    qtbot.addWidget(panel)

    spy = SpySettingsController()
    panel._settings_controller = spy

    class FakeServiceDialog:
        def __init__(self, parent=None, *, naziv="", trajanje=30, buffer=0):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def values(self):
            return ("Nova", 45, 15)

    monkeypatch.setattr(settings_panel_mod, "ServiceDialog", FakeServiceDialog)

    add_button = next(b for b in panel.findChildren(QPushButton) if b.text() == "Dodaj uslugu")
    add_button.click()

    assert spy.calls == [("add_service", "Nova", 45, 15)]


def test_update_service_delegira_controlleru(qtbot, monkeypatch) -> None:
    store = SpyStore()
    panel = SettingsPanel(store)
    qtbot.addWidget(panel)

    spy = SpySettingsController()
    panel._settings_controller = spy

    class FakeServiceDialog:
        def __init__(self, parent=None, *, naziv="", trajanje=30, buffer=0):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def values(self):
            return ("Izmijenjena", 60, 20)

    monkeypatch.setattr(settings_panel_mod, "ServiceDialog", FakeServiceDialog)

    panel.services_table.setCurrentCell(0, 0)  # selektuj prvu uslugu
    edit_button = next(b for b in panel.findChildren(QPushButton) if b.text() == "Uredi uslugu")
    edit_button.click()

    assert spy.calls == [("update_service", 1, "Izmijenjena", 60, 20)]


def test_set_working_hours_delegira_controlleru(qtbot) -> None:
    store = SpyStore()
    panel = SettingsPanel(store)
    qtbot.addWidget(panel)

    spy = SpySettingsController()
    panel._settings_controller = spy

    panel.doctor_combo.setCurrentIndex(0)  # Ljubo (id=1)
    panel.day_combo.setCurrentIndex(0)  # Ponedjeljak (dan=1)
    intervals = [(time(8, 0), time(9, 0))]
    panel._set_hours(intervals)

    assert spy.calls == [("set_working_hours", 1, 1, intervals)]


# --- REF-12: SettingsController čista delegacija (unit) ---


def test_settings_controller_je_cista_delegacija() -> None:
    calls: list = []

    class Store:
        def set_doctor_active(self, doctor_id, active):
            calls.append(("set_doctor_active", doctor_id, active))
            return "dto"

        def add_service(self, naziv, trajanje, buffer):
            calls.append(("add_service", naziv, trajanje, buffer))

        def update_service(self, service_id, naziv, trajanje, buffer):
            calls.append(("update_service", service_id, naziv, trajanje, buffer))

        def set_working_hours(self, doctor_id, dan, intervals):
            calls.append(("set_working_hours", doctor_id, dan, intervals))

    controller = SettingsController(Store())
    assert controller.set_doctor_active(1, False) == "dto"
    controller.add_service("Nova", 45, 15)
    controller.update_service(2, "X", 30, 0)
    controller.set_working_hours(1, 1, [(time(8, 0), time(9, 0))])

    assert calls == [
        ("set_doctor_active", 1, False),
        ("add_service", "Nova", 45, 15),
        ("update_service", 2, "X", 30, 0),
        ("set_working_hours", 1, 1, [(time(8, 0), time(9, 0))]),
    ]


def test_settings_controller_propagira_izuzetak() -> None:
    class Store:
        def set_doctor_active(self, doctor_id, active):
            raise ValueError("x")

        def add_service(self, *args):
            pass

        def update_service(self, *args):
            pass

        def set_working_hours(self, *args):
            pass

    controller = SettingsController(Store())
    with pytest.raises(ValueError):
        controller.set_doctor_active(1, True)
