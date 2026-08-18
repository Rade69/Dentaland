"""Dijalog za unos novog termina (Faza 0 — staff-facing unos)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class AppointmentDialog(QDialog):
    """Skuplja ime/telefon/email/uslugu/vrijeme/napomenu — bez validacije.

    Namjerno nema validacije: Faza 0 sveska je slobodna forma, napomena je
    slobodan tekst, a ništa ne smije da "smeta" pri brzom unosu.

    ``start`` polje je slobodan ``QDateTimeEdit`` (isti obrazac kao
    ``ConfirmationDialog`` za potvrdu web zahtjeva) — predlaže vrijeme sa
    kojim je dijalog otvoren (npr. klik u mreži), ali osoblje može upisati
    BILO KOJI tačan minut, ne samo pun sat/pola sata. Klik-preciznost u
    mreži je samo pogodan predlog, ne ograničenje.
    """

    def __init__(self, services: list[str], start: datetime, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novi termin")
        self._zone = start.tzinfo

        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.service_combo = QComboBox()
        self.service_combo.addItems(services)
        self.start_edit = QDateTimeEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("dd.MM.yyyy. HH:mm")
        self.start_edit.setDateTime(
            QDateTime(QDate(start.year, start.month, start.day), QTime(start.hour, start.minute))
        )
        self.note_edit = QPlainTextEdit()

        form = QFormLayout()
        form.addRow("Ime i prezime:", self.name_edit)
        form.addRow("Telefon:", self.phone_edit)
        form.addRow("Email:", self.email_edit)
        form.addRow("Usluga:", self.service_combo)
        form.addRow("Datum i vrijeme:", self.start_edit)
        form.addRow("Napomena:", self.note_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_data(self) -> dict[str, Any]:
        start = cast(datetime, self.start_edit.dateTime().toPython())
        if start.tzinfo is None:
            start = start.replace(tzinfo=self._zone or ZoneInfo("Europe/Sarajevo"))
        return {
            "patient_name": self.name_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "service": self.service_combo.currentText(),
            "note": self.note_edit.toPlainText(),
            "start": start,
        }
