"""Glavni prozor desktop aplikacije."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDialog, QMainWindow

from desktop.fake_data import DEFAULT_DURATION_MINUTES, FakeStore
from desktop.views.appointment_dialog import AppointmentDialog
from desktop.views.week_view import WeekView


class MainWindow(QMainWindow):
    """Sedmični raspored + alatna traka (štampa je TODO stub)."""

    def __init__(self, store: FakeStore, week_start: date | None = None, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Dentaland — Raspored")

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        self.week_view = WeekView(store, week_start, parent=self)
        self.setCentralWidget(self.week_view)

        toolbar = self.addToolBar("Alati")
        self.print_action = QAction("Štampaj raspored", self)
        self.print_action.triggered.connect(self._on_print)
        toolbar.addAction(self.print_action)

        self.week_view.slot_selected.connect(self._on_slot_selected)

    def _on_slot_selected(self, start) -> None:
        dialog = AppointmentDialog(self.store.services(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.store.create(
                patient_name=data["patient_name"],
                phone=data["phone"],
                email=data["email"],
                service=data["service"],
                note=data["note"],
                start=start,
                end=start + timedelta(minutes=DEFAULT_DURATION_MINUTES),
            )
            self.week_view.refresh()

    def _on_print(self) -> None:
        # TODO: prava štampa (QPrinter/QTextDocument) — zaseban budući zadatak.
        self.statusBar().showMessage("Štampa rasporeda — TODO (stub)", 5000)
