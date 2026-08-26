"""Unified editor za Novi/Uredi termin (Faza B redizajna).

Jedan dijalog za oba toka. Prima plain podatke (NE store/SQLAlchemy objekte):
doktori kao ``(id, ime)``, usluge kao ``(naziv, trajanje_min)`` — MainWindow
(orkestrator) ih dohvaća iz store-a. Dijalog ne zna za bazu; minimizacija i
trajanje zavise od toga šta mu se prosledi.

Vrijeme se prikazuje i vraća u ``Europe/Sarajevo`` (timezone-aware pravilo).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTimeEdit,
    QWidget,
)

from dentaland.timezone import SARAJEVO
from desktop.views.dialogs.base_dialog import BaseDialog


class AppointmentEditorDialog(BaseDialog):
    """Jedan editor za kreiranje i uređivanje termina.

    Create mode: ``appointment=None``; datum/vrijeme se prefilluju iz ``start``,
    doktor se preselektuje preko ``selected_doctor_id`` (ili ostaje na
    "Izaberi doktora" kad je aktivni filter "Svi doktori").

    Edit mode: ``appointment`` nosi postojeći DTO (duck-typed — koristi
    ``patient_name``/``phone``/``email``/``doctor_id``/``service``/``note``/
    ``start``/``end``); trajanje se prefilluje iz ``end - start``.
    """

    def __init__(
        self,
        doctors: list[tuple[int, str]],
        service_options: list[tuple[str, int]],
        start: datetime,
        *,
        appointment: Any | None = None,
        selected_doctor_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        is_edit = appointment is not None
        super().__init__("Uredi termin" if is_edit else "Novi termin", parent, icon="calendar")

        self._doctors = doctors
        self._service_durations = {name: duration for name, duration in service_options}

        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()

        self.doctor_combo = QComboBox()
        self.doctor_combo.addItem("— Izaberi doktora —", None)
        for doctor_id, ime in doctors:
            self.doctor_combo.addItem(ime, doctor_id)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy.")

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")

        self.duration_edit = QSpinBox()
        self.duration_edit.setRange(5, 480)
        self.duration_edit.setSuffix(" min")

        self.service_combo = QComboBox()
        for name, _duration in service_options:
            self.service_combo.addItem(name)

        self.note_edit = QPlainTextEdit()

        self._set_start(start)
        if is_edit:
            self._prefill(appointment)
        elif selected_doctor_id is not None:
            self._select_doctor(selected_doctor_id)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # Pacijent | Doktor (jedan red)
        grid.addWidget(self._field_label("Pacijent *"), 0, 0)
        grid.addWidget(self.name_edit, 1, 0)
        grid.addWidget(self._field_label("Doktor *"), 0, 1)
        grid.addWidget(self.doctor_combo, 1, 1)

        # Datum | Vrijeme | Trajanje (jedan red, tri kolone)
        grid.addWidget(self._field_label("Datum *"), 2, 0)
        grid.addWidget(self.date_edit, 3, 0)
        grid.addWidget(self._field_label("Vrijeme *"), 2, 1)
        grid.addWidget(self.time_edit, 3, 1)
        grid.addWidget(self._field_label("Trajanje *"), 2, 2)
        grid.addWidget(self.duration_edit, 3, 2)

        # Telefon | Email
        grid.addWidget(self._field_label("Telefon"), 4, 0)
        grid.addWidget(self.phone_edit, 5, 0)
        grid.addWidget(self._field_label("Email"), 4, 1)
        grid.addWidget(self.email_edit, 5, 1)

        # Usluga (puna širina)
        grid.addWidget(self._field_label("Usluga *"), 6, 0, 1, 3)
        grid.addWidget(self.service_combo, 7, 0, 1, 3)

        # Napomena (puna širina)
        grid.addWidget(self._field_label("Napomena"), 8, 0, 1, 3)
        grid.addWidget(self.note_edit, 9, 0, 1, 3)

        self.body_layout().addLayout(grid)

        # Podrazumijevano trajanje iz prve usluge; promjena usluge ga ažurira.
        # U edit modu trajanje je već postavljeno iz _prefill() (end - start)
        # i ne smije se odmah prepisati defaultom usluge.
        if not is_edit and self.service_combo.count():
            self._apply_service_duration(self.service_combo.currentIndex())
        self.service_combo.currentIndexChanged.connect(self._apply_service_duration)

        self.add_secondary_button("Odustani")
        self.add_primary_button("Sačuvaj izmjene" if is_edit else "Sačuvaj termin")

    # ---- interni prikaz ----

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("editorFieldLabel")
        return label

    def _set_start(self, start: datetime) -> None:
        local = (
            start.astimezone(SARAJEVO)
            if start.tzinfo is not None
            else start.replace(tzinfo=SARAJEVO)
        )
        self.date_edit.setDate(QDate(local.year, local.month, local.day))
        self.time_edit.setTime(QTime(local.hour, local.minute))

    def _select_doctor(self, doctor_id: int | None) -> None:
        index = self.doctor_combo.findData(doctor_id)
        if index >= 0:
            self.doctor_combo.setCurrentIndex(index)

    def _apply_service_duration(self, index: int) -> None:
        name = self.service_combo.itemText(index)
        duration = self._service_durations.get(name)
        if duration is not None:
            self.duration_edit.setValue(duration)

    def _prefill(self, appointment: Any) -> None:
        self.name_edit.setText(getattr(appointment, "patient_name", ""))
        self.phone_edit.setText(getattr(appointment, "phone", ""))
        self.email_edit.setText(getattr(appointment, "email", ""))
        self.note_edit.setPlainText(getattr(appointment, "note", ""))
        start = getattr(appointment, "start", None)
        end = getattr(appointment, "end", None)
        if start is not None:
            self._set_start(start)
            if end is not None:
                duration = int((end - start).total_seconds() / 60)
                if 5 <= duration <= 480:
                    self.duration_edit.setValue(duration)
        self._select_doctor(getattr(appointment, "doctor_id", None))
        service_index = self.service_combo.findText(getattr(appointment, "service", ""))
        if service_index >= 0:
            self.service_combo.setCurrentIndex(service_index)

    # ---- javni API ----

    def selected_doctor_id(self) -> int | None:
        return self.doctor_combo.currentData()

    def get_data(self) -> dict[str, Any]:
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
        return {
            "patient_name": self.name_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "doctor_id": self.selected_doctor_id(),
            "service": self.service_combo.currentText(),
            "note": self.note_edit.toPlainText(),
            "start": start,
            "duration_min": self.duration_edit.value(),
        }

    def validate(self) -> str | None:
        """Vrati poruku greške ili ``None`` ako je unos ispravan."""
        if not self.name_edit.text().strip():
            return "Unesite ime pacijenta."
        if self._doctors and self.selected_doctor_id() is None:
            return "Izaberite doktora."
        if self.service_combo.count() and not self.service_combo.currentText():
            return "Izaberite uslugu."
        return None

    def accept(self) -> None:
        error = self.validate()
        if error is not None:
            self.show_error(error)
            return
        super().accept()
