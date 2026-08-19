"""Detalji termina — read-only prikaz + uslovne akcije (Faza C redizajna).

Status NIJE dropdown: prikazuje se badge sa trenutnim stanjem i uslovne
akcije. Terminalni statusi (COMPLETED/NO_SHOW/CANCELLED) nemaju povratne
akcije. Dijalog NE poziva store — samo bira akciju i vraća je pozivaocu
(MainWindow orkestrira).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QWidget

from desktop.views.dialogs.base_dialog import BaseDialog
from desktop.views.week_view import STATUS_META, _status_key

SARAJEVO = ZoneInfo("Europe/Sarajevo")


class AppointmentDetailsDialog(BaseDialog):
    """Prikaz termina + status badge + uslovne akcije."""

    def __init__(self, appointment: Any, parent: QWidget | None = None) -> None:
        super().__init__("Detalji termina", parent)
        self.appointment = appointment
        self._selected_action: str | None = None
        self._action_buttons: list[QPushButton] = []

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)

        def add_row(row: int, label: str, value: str) -> None:
            key = QLabel(label)
            key.setObjectName("detailLabel")
            val = QLabel(value)
            val.setObjectName("detailValue")
            val.setWordWrap(True)
            grid.addWidget(key, row, 0)
            grid.addWidget(val, row, 1)

        start = getattr(appointment, "start", None)
        end = getattr(appointment, "end", None)
        add_row(0, "Pacijent", getattr(appointment, "patient_name", "") or "—")
        add_row(1, "Telefon", getattr(appointment, "phone", "") or "—")
        add_row(2, "Email", getattr(appointment, "email", "") or "—")
        add_row(3, "Datum", self._fmt_date(start))
        add_row(4, "Vrijeme", self._fmt_time(start, end))
        add_row(5, "Trajanje", self._fmt_duration(start, end))
        add_row(6, "Doktor", getattr(appointment, "doctor_name", "") or "—")
        add_row(7, "Usluga", getattr(appointment, "service", "") or "—")
        add_row(8, "Napomena", getattr(appointment, "note", "") or "—")
        self.body_layout().addLayout(grid)

        key = _status_key(appointment)
        symbol, color, label = STATUS_META[key]
        self.status_badge = QLabel(f"{symbol} {label}")
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: 700; "
            "background-color: #f4fafb; border: 1px solid #c9dce3; "
            "border-radius: 7px; padding: 8px;"
        )
        self.body_layout().addWidget(self.status_badge)

        terminal = key in {"completed", "cancelled"}
        if not terminal:
            self._add_section("Dostupne akcije")
            if key != "confirmed":
                self._add_action("Potvrdi termin", "confirm")
            if getattr(appointment, "arrived_at", None) is None:
                self._add_action("Pacijent je stigao", "arrived")
            self._add_action("Označi kao završen", "completed")
            self._add_action("Označi 'nije došao'", "no_show")

            self._add_section("Operativne akcije")
            self._add_action("Uredi termin", "edit")
            self._add_action("Pomjeri termin", "move")
            self._add_action("Otkaži termin", "cancel")

        self.add_secondary_button("Zatvori")
        self._apply_style()

    def _add_section(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("detailSection")
        self.body_layout().addWidget(label)

    def _add_action(self, label: str, action: str) -> None:
        button = QPushButton(label)
        button.setObjectName("detailActionButton")
        button.clicked.connect(lambda: self._choose(action))
        self.body_layout().addWidget(button)
        self._action_buttons.append(button)

    def _choose(self, action: str) -> None:
        self._selected_action = action
        self.accept()

    def selected_action(self) -> str | None:
        return self._selected_action

    @staticmethod
    def _fmt_date(start: datetime | None) -> str:
        if start is None:
            return "—"
        return start.astimezone(SARAJEVO).strftime("%d.%m.%Y.")

    @staticmethod
    def _fmt_time(start: datetime | None, end: datetime | None) -> str:
        if start is None or end is None:
            return "—"
        return f"{start.astimezone(SARAJEVO):%H:%M} – {end.astimezone(SARAJEVO):%H:%M}"

    @staticmethod
    def _fmt_duration(start: datetime | None, end: datetime | None) -> str:
        if start is None or end is None:
            return "—"
        return f"{int((end - start).total_seconds() / 60)} min"

    def _apply_style(self) -> None:
        self.setStyleSheet(
            self.styleSheet()
            + """
            #detailLabel { color: #718096; font-weight: 600; }
            #detailValue { color: #10213d; }
            #detailSection {
                color: #31578a; font-weight: 700; margin-top: 8px;
            }
            #detailActionButton {
                background-color: #ffffff; color: #10213d;
                border: 1px solid #cad8e2; border-radius: 6px;
                min-height: 34px; padding: 2px 12px; text-align: left;
            }
            #detailActionButton:hover { background-color: #eef8f9; border-color: #078f96; }
            """
        )
