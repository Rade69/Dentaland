"""Controller za print workflow (REF-07).

Premješten iz ``MainWindow``: meni za štampu (sedmica/dan/PDF), priprema
dokumenta i dijalog za izbor dana. ``print_schedule.py`` (servisni sloj) i
``print_document.py`` ostaju netaknuti — Controller ih samo poziva.

``week_start_provider`` je callable koji vraća prikazani početak sedmice
(``ScheduleController.week_start``), jer print zavisi od trenutnog perioda.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from PySide6.QtCore import QDate
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from dentaland.services.print_schedule import build_day_schedule, build_week_schedule
from desktop.print_document import build_day_document, build_week_document, preview_document


class PrintController:
    """Print workflow, nezavisan od ``MainWindow`` konkretne klase."""

    def __init__(
        self,
        store: Any,
        parent_widget: QWidget,
        week_start_provider: Callable[[], date],
    ) -> None:
        self._store = store
        self._parent_widget = parent_widget
        self._week_start_provider = week_start_provider

    def on_print(self) -> None:
        menu = QMenu(self._parent_widget)
        week_action = menu.addAction("Štampaj prikazanu sedmicu")
        day_action = menu.addAction("Štampaj jedan dan…")
        pdf_action = menu.addAction("Sačuvaj kao PDF")
        chosen = menu.exec(QCursor.pos())
        if chosen == week_action:
            self.print_week()
        elif chosen == day_action:
            self.print_day()
        elif chosen == pdf_action:
            self.save_pdf()

    def print_week(self) -> None:
        schedule = build_week_schedule(self._store, self._week_start_provider())
        preview_document(self._parent_widget, build_week_document(schedule), landscape=True)

    def print_day(self) -> None:
        day = self._pick_day()
        if day is None:
            return
        schedule = build_day_schedule(self._store, day)
        preview_document(self._parent_widget, build_day_document(schedule), landscape=False)

    def save_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self._parent_widget, "Sačuvaj raspored kao PDF", "raspored.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        schedule = build_week_schedule(self._store, self._week_start_provider())
        preview_document(
            self._parent_widget, build_week_document(schedule), landscape=True, pdf_path=path
        )

    def _pick_day(self) -> date | None:
        week_start = self._week_start_provider()
        dialog = QDialog(self._parent_widget)
        dialog.setWindowTitle("Izaberite dan za štampu")
        calendar = QCalendarWidget(dialog)
        calendar.setSelectedDate(
            QDate(week_start.year, week_start.month, week_start.day)
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout = QVBoxLayout(dialog)
        layout.addWidget(calendar)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        selected = calendar.selectedDate()
        return date(selected.year(), selected.month(), selected.day())
