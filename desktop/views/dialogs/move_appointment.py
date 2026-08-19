"""Pomjeri termin — stilizovani modal (Faza C redizajna).

Prikazuje trenutno vrijeme i trajanje, nudi novi datum/vrijeme/trajanje.
Overlap provjerava pozivalac (MainWindow) kroz ``store.move`` — greška se
vraća inline u ovaj modal (ostaje otvoren).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import QDateEdit, QFormLayout, QLabel, QSpinBox, QTimeEdit, QWidget

from desktop.views.dialogs.base_dialog import BaseDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")


class MoveAppointmentDialog(BaseDialog):
    """Novi datum/vrijeme za postojeći termin; trajanje ostaje vidljivo."""

    def __init__(self, appointment: Any, parent: QWidget | None = None) -> None:
        super().__init__("Pomjeri termin", parent)
        self.appointment = appointment

        start = appointment.start.astimezone(SARAJEVO)
        end = appointment.end.astimezone(SARAJEVO)
        duration = max(int((end - start).total_seconds() / 60), 5)

        current = QLabel(f"Trenutno: {start:%d.%m.%Y.} · {start:%H:%M}–{end:%H:%M}")
        current.setObjectName("moveCurrent")
        self.body_layout().addWidget(current)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy.")
        self.date_edit.setDate(QDate(start.year, start.month, start.day))

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(start.hour, start.minute))

        self.duration_edit = QSpinBox()
        self.duration_edit.setRange(5, 480)
        self.duration_edit.setSuffix(" min")
        self.duration_edit.setValue(duration)

        form = QFormLayout()
        form.addRow("Novi datum *", self.date_edit)
        form.addRow("Novo vrijeme *", self.time_edit)
        form.addRow("Trajanje", self.duration_edit)
        self.body_layout().addLayout(form)

        self.add_secondary_button("Odustani")
        self.add_primary_button("Pomjeri termin")

    def get_data(self) -> tuple[datetime, int]:
        """Vrati ``(novi_start, trajanje_min)`` — start u Europe/Sarajevo."""
        date_val = self.date_edit.date()
        time_val = self.time_edit.time()
        start = datetime(
            date_val.year(),
            date_val.month(),
            date_val.day(),
            time_val.hour(),
            time_val.minute(),
            tzinfo=SARAJEVO,
        )
        return start, self.duration_edit.value()
