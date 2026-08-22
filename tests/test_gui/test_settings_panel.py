"""GUI testovi za postavke (DENT-IMPROVE-005)."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QPushButton, QTableWidget, QTabWidget

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
