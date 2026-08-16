"""Glavni prozor desktop aplikacije."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QInputDialog,
    QMainWindow,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from dentaland.services import OverlapError
from desktop.fake_data import DEFAULT_DURATION_MINUTES
from desktop.views.appointment_dialog import AppointmentDialog
from desktop.views.week_view import WeekView


class MainWindow(QMainWindow):
    """Sedmični raspored + filter tabovi doktora + alatna traka (štampa stub)."""

    def __init__(self, store, week_start: date | None = None, parent=None):
        super().__init__(parent)
        self.store = store
        self._current_doctor_id: int | None = None
        self._has_doctors = False
        self._doctors: list = []
        self.setWindowTitle("Dentaland — Raspored")

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        self.week_view = WeekView(store, week_start, parent=self)
        self.doctor_tabs = self._build_doctor_tabs()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        if self.doctor_tabs is not None:
            layout.addWidget(self.doctor_tabs)
        layout.addWidget(self.week_view)
        self.setCentralWidget(central)

        toolbar = self.addToolBar("Alati")
        self.print_action = QAction("Štampaj raspored", self)
        self.print_action.triggered.connect(self._on_print)
        toolbar.addAction(self.print_action)

        self.week_view.slot_selected.connect(self._on_slot_selected)

    def _build_doctor_tabs(self) -> QTabBar | None:
        doctors_fn = getattr(self.store, "doctors", None)
        if not callable(doctors_fn):
            return None
        self._doctors = list(doctors_fn())
        self._has_doctors = bool(self._doctors)
        if not self._doctors:
            return None
        tabs = QTabBar()
        tabs.addTab("Svi doktori")
        for doctor in self._doctors:
            tabs.addTab(f"Dr {doctor.ime}")
        self._tab_doctor_ids: list[int | None] = [None] + [d.id for d in self._doctors]
        tabs.currentChanged.connect(self._on_tab_changed)
        return tabs

    def _on_tab_changed(self, index: int) -> None:
        doctor_id = self._tab_doctor_ids[index]
        self._current_doctor_id = doctor_id
        self.week_view.set_filter(doctor_id)

    def _doctor_for_new_appointment(self) -> int | None:
        """Odredi doktora za novi termin; ``None`` znači "nema doktora/odustao"."""
        if not self._has_doctors:
            return None
        if self._current_doctor_id is not None:
            return self._current_doctor_id
        names = [d.ime for d in self._doctors]
        chosen, ok = QInputDialog.getItem(self, "Doktor", "Koji doktor?", names, 0, False)
        if not ok:
            return None
        return self._doctors[names.index(chosen)].id

    def _on_slot_selected(self, start) -> None:
        doctor_id = self._doctor_for_new_appointment()
        if self._has_doctors and doctor_id is None:
            return  # ne kreiraj termin bez jasnog vlasnika
        if doctor_id is not None and hasattr(self.store, "set_doctor"):
            self.store.set_doctor(doctor_id)

        dialog = AppointmentDialog(self.store.services(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.store.create(
                    patient_name=data["patient_name"],
                    phone=data["phone"],
                    email=data["email"],
                    service=data["service"],
                    note=data["note"],
                    start=start,
                    end=start + timedelta(minutes=DEFAULT_DURATION_MINUTES),
                )
            except OverlapError as exc:
                self.statusBar().showMessage(str(exc), 5000)
                return
            self.week_view.refresh()

    def _on_print(self) -> None:
        # TODO: prava štampa (QPrinter/QTextDocument) — zaseban budući zadatak.
        self.statusBar().showMessage("Štampa rasporeda — TODO (stub)", 5000)
