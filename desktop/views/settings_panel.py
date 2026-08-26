"""Postavke — doktori, usluge i radno vrijeme (DENT-IMPROVE-005).

Minimalne postavke koje ordinacija stvarno treba. Business/database operacije
idu kroz servisni sloj (``store``), ovaj modul ne uvozi SQLAlchemy.
"""

from __future__ import annotations

from datetime import time
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.controllers.settings_controller import SettingsController
from desktop.views.dialogs.base_dialog import BaseDialog

DAN_NAMES = [
    "Ponedjeljak",
    "Utorak",
    "Srijeda",
    "Četvrtak",
    "Petak",
    "Subota",
    "Nedjelja",
]


class ServiceDialog(BaseDialog):
    """Dodaj/uredi uslugu — naziv, trajanje, buffer."""

    def __init__(
        self, parent: QWidget | None = None, *, naziv: str = "", trajanje: int = 30, buffer: int = 0
    ) -> None:
        super().__init__("Usluga", parent, icon="settings")
        form = QFormLayout()
        self.naziv_edit = QComboBox()
        self.naziv_edit.setEditable(True)
        self.naziv_edit.setCurrentText(naziv)
        form.addRow("Naziv", self.naziv_edit)
        self.trajanje_spin = QSpinBox()
        self.trajanje_spin.setRange(1, 600)
        self.trajanje_spin.setValue(trajanje)
        self.trajanje_spin.setSuffix(" min")
        form.addRow("Trajanje", self.trajanje_spin)
        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(0, 120)
        self.buffer_spin.setValue(buffer)
        self.buffer_spin.setSuffix(" min")
        form.addRow("Buffer", self.buffer_spin)
        self.body_layout().addLayout(form)
        self.add_secondary_button("Odustani")
        self.add_primary_button("Sačuvaj")

    def values(self) -> tuple[str, int, int]:
        return (
            self.naziv_edit.currentText().strip(),
            self.trajanje_spin.value(),
            self.buffer_spin.value(),
        )


class IntervalDialog(BaseDialog):
    """Dodaj interval radnog vremena — od/do."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Interval radnog vremena", parent, icon="clock")
        form = QFormLayout()
        self.od_edit = QTimeEdit()
        self.od_edit.setDisplayFormat("HH:mm")
        self.od_edit.setTime(self.od_edit.time().fromString("08:00", "HH:mm"))
        form.addRow("Od", self.od_edit)
        self.do_edit = QTimeEdit()
        self.do_edit.setDisplayFormat("HH:mm")
        self.do_edit.setTime(self.do_edit.time().fromString("09:00", "HH:mm"))
        form.addRow("Do", self.do_edit)
        self.body_layout().addLayout(form)
        self.add_secondary_button("Odustani")
        self.add_primary_button("Sačuvaj")

    def values(self) -> tuple[time, time]:
        qod = self.od_edit.time()
        qdo = self.do_edit.time()
        return time(qod.hour(), qod.minute()), time(qdo.hour(), qdo.minute())


class SettingsPanel(QScrollArea):
    """Tri taba postavki; svaka izmjena emituje ``changed``."""

    changed = Signal()

    def __init__(self, store: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._settings_controller = SettingsController(store)
        self.setObjectName("settingsPanel")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(26, 18, 14, 14)
        title = QLabel("Postavke")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_doctors_tab(), "Doktori")
        self.tabs.addTab(self._build_services_tab(), "Usluge")
        self.tabs.addTab(self._build_hours_tab(), "Radno vrijeme")
        layout.addWidget(self.tabs)

        self.setWidget(container)
        self.refresh()

    # ---- Doktori ----

    def _build_doctors_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Aktivan doktor se prikazuje u filteru i dijalozima."))
        self.doctors_layout = QVBoxLayout()
        layout.addLayout(self.doctors_layout)
        layout.addStretch()
        return widget

    def _refresh_doctors(self) -> None:
        while self.doctors_layout.count():
            item = self.doctors_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        doctors_fn = getattr(self.store, "list_doctors", None)
        for doctor in doctors_fn() if callable(doctors_fn) else []:
            checkbox = QCheckBox(doctor.ime)
            checkbox.setChecked(doctor.aktivan)
            checkbox.toggled.connect(
                lambda checked, doctor_id=doctor.id: self._on_doctor_toggle(doctor_id, checked)
            )
            self.doctors_layout.addWidget(checkbox)

    def _on_doctor_toggle(self, doctor_id: int, active: bool) -> None:
        try:
            self._settings_controller.set_doctor_active(doctor_id, active)
        except ValueError as exc:
            QMessageBox.warning(self, "Postavke", str(exc))
            return
        self.changed.emit()

    # ---- Usluge ----

    def _build_services_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.services_table = QTableWidget(0, 3)
        self.services_table.setHorizontalHeaderLabels(["Naziv", "Trajanje (min)", "Buffer (min)"])
        self.services_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.services_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.services_table)
        buttons = QHBoxLayout()
        add_button = QPushButton("Dodaj uslugu")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._on_add_service)
        edit_button = QPushButton("Uredi uslugu")
        edit_button.clicked.connect(self._on_edit_service)
        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        return widget

    def _refresh_services(self) -> None:
        options_fn = getattr(self.store, "service_options", None)
        options = list(options_fn()) if callable(options_fn) else []
        self.services_table.setRowCount(len(options))
        for row, option in enumerate(options):
            self.services_table.setItem(row, 0, QTableWidgetItem(option.naziv))
            self.services_table.setItem(row, 1, QTableWidgetItem(str(option.trajanje_min)))
            self.services_table.setItem(row, 2, QTableWidgetItem(str(option.buffer_min)))
            naziv_item = self.services_table.item(row, 0)
            assert naziv_item is not None
            naziv_item.setData(Qt.ItemDataRole.UserRole, option.id)

    def _selected_service(self) -> tuple[int, str, int, int] | None:
        row = self.services_table.currentRow()
        if row < 0:
            return None
        item = self.services_table.item(row, 0)
        if item is None:
            return None
        service_id = item.data(Qt.ItemDataRole.UserRole)
        naziv = item.text()
        trajanje_item = self.services_table.item(row, 1)
        buffer_item = self.services_table.item(row, 2)
        assert trajanje_item is not None
        assert buffer_item is not None
        trajanje = int(trajanje_item.text())
        buffer = int(buffer_item.text())
        return service_id, naziv, trajanje, buffer

    def _on_add_service(self) -> None:
        dialog = ServiceDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        naziv, trajanje, buffer = dialog.values()
        try:
            self._settings_controller.add_service(naziv, trajanje, buffer)
        except ValueError as exc:
            QMessageBox.warning(self, "Postavke", str(exc))
            return
        self.refresh()
        self.changed.emit()

    def _on_edit_service(self) -> None:
        selected = self._selected_service()
        if selected is None:
            QMessageBox.information(self, "Postavke", "Izaberite uslugu.")
            return
        service_id, naziv, trajanje, buffer = selected
        dialog = ServiceDialog(self, naziv=naziv, trajanje=trajanje, buffer=buffer)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_naziv, new_trajanje, new_buffer = dialog.values()
        try:
            self._settings_controller.update_service(
                service_id, new_naziv, new_trajanje, new_buffer
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Postavke", str(exc))
            return
        self.refresh()
        self.changed.emit()

    # ---- Radno vrijeme ----

    def _build_hours_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QHBoxLayout()
        self.doctor_combo = QComboBox()
        form.addWidget(QLabel("Doktor"))
        form.addWidget(self.doctor_combo)
        self.day_combo = QComboBox()
        for index, name in enumerate(DAN_NAMES, start=1):
            self.day_combo.addItem(name, index)
        form.addWidget(QLabel("Dan"))
        form.addWidget(self.day_combo)
        form.addStretch()
        layout.addLayout(form)

        self.intervals_list = QListWidget()
        layout.addWidget(self.intervals_list)

        buttons = QHBoxLayout()
        add_button = QPushButton("Dodaj interval")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._on_add_interval)
        remove_button = QPushButton("Ukloni interval")
        remove_button.clicked.connect(self._on_remove_interval)
        save_button = QPushButton("Sačuvaj")
        save_button.clicked.connect(self._on_save_hours)
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addWidget(save_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.doctor_combo.currentIndexChanged.connect(lambda _index: self._refresh_hours())
        self.day_combo.currentIndexChanged.connect(lambda _index: self._refresh_hours())
        return widget

    def _refresh_doctors_combo(self) -> None:
        current = self.doctor_combo.currentData()
        self.doctor_combo.clear()
        doctors_fn = getattr(self.store, "doctors", None)
        for doctor in doctors_fn() if callable(doctors_fn) else []:
            self.doctor_combo.addItem(doctor.ime, doctor.id)
        if current is not None:
            index = self.doctor_combo.findData(current)
            if index >= 0:
                self.doctor_combo.setCurrentIndex(index)

    def _current_working_hours(self) -> list[tuple[time, time]]:
        doctor_id = self.doctor_combo.currentData()
        dan = self.day_combo.currentData()
        if doctor_id is None or dan is None:
            return []
        hours_fn = getattr(self.store, "list_working_hours", None)
        rows = hours_fn(doctor_id) if callable(hours_fn) else []
        return [(row.od_local, row.do_local) for row in rows if row.dan_u_sedmici == dan]

    def _refresh_hours(self) -> None:
        self.intervals_list.clear()
        for od_local, do_local in self._current_working_hours():
            self.intervals_list.addItem(f"{od_local:%H:%M} – {do_local:%H:%M}")

    def _on_add_interval(self) -> None:
        dialog = IntervalDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        od_local, do_local = dialog.values()
        intervals = self._current_working_hours() + [(od_local, do_local)]
        self._set_hours(intervals)

    def _on_remove_interval(self) -> None:
        row = self.intervals_list.currentRow()
        if row < 0:
            return
        intervals = self._current_working_hours()
        if 0 <= row < len(intervals):
            intervals.pop(row)
        self._set_hours(intervals)

    def _on_save_hours(self) -> None:
        self._set_hours(self._current_working_hours())

    def _set_hours(self, intervals: list[tuple[time, time]]) -> None:
        doctor_id = self.doctor_combo.currentData()
        dan = self.day_combo.currentData()
        if doctor_id is None or dan is None:
            return
        try:
            self._settings_controller.set_working_hours(doctor_id, dan, intervals)
        except ValueError as exc:
            QMessageBox.warning(self, "Postavke", str(exc))
            return
        self._refresh_hours()
        self.changed.emit()

    # ---- refresh ----

    def refresh(self) -> None:
        self._refresh_doctors()
        self._refresh_services()
        self._refresh_doctors_combo()
        self._refresh_hours()
