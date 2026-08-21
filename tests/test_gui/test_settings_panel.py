"""GUI testovi za postavke (DENT-IMPROVE-005)."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QTableWidget, QTabWidget

from desktop.views.settings_panel import SettingsPanel


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
