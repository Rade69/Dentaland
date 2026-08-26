"""Detalji termina — read-only prikaz + uslovne akcije (Faza C, vizuelni polish B2).

Dvokolonski layout prema mockapu: lijevo podaci pacijenta (sa ikonicom uz
svaki red), desno "Status termina" sekcija — istaknut status + dostupne
akcije. Status NIJE dropdown. Terminalni statusi nemaju povratne akcije.
Dijalog NE poziva store — samo bira akciju i vraća je pozivaocu.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from dentaland.timezone import SARAJEVO
from desktop.views.dialogs.base_dialog import BaseDialog
from desktop.views.week_view import STATUS_META, _status_key

_STATUS_BG = {
    "confirmed": "#e8f7ee",
    "waiting": "#fff4e6",
    "arrived": "#e8f1fd",
    "completed": "#f3eefd",
    "no_show": "#fdeee4",
    "cancelled": "#fdecef",
}


class AppointmentDetailsDialog(BaseDialog):
    """Prikaz termina + status highlight + uslovne akcije (dvokolonski)."""

    def __init__(self, appointment: Any, parent: QWidget | None = None) -> None:
        super().__init__("Detalji termina", parent, icon="calendar")
        self.appointment = appointment
        self._selected_action: str | None = None
        self._action_buttons: list[QPushButton] = []
        self._right = QVBoxLayout()
        self._right.setSpacing(8)

        columns = QHBoxLayout()
        columns.setSpacing(20)

        # LIJEVO — podaci pacijenta sa ikonicama
        info = QGridLayout()
        info.setHorizontalSpacing(8)
        info.setVerticalSpacing(8)
        info.setColumnStretch(2, 1)

        start = getattr(appointment, "start", None)
        end = getattr(appointment, "end", None)
        rows = [
            ("user", "Pacijent", getattr(appointment, "patient_name", "") or "—"),
            ("phone", "Telefon", getattr(appointment, "phone", "") or "—"),
            ("mail", "Email", getattr(appointment, "email", "") or "—"),
            ("calendar", "Datum", self._fmt_date(start)),
            ("clock", "Vrijeme", self._fmt_time(start, end)),
            ("clock", "Trajanje", self._fmt_duration(start, end)),
            ("user", "Doktor", getattr(appointment, "doctor_name", "") or "—"),
            ("tooth", "Usluga", getattr(appointment, "service", "") or "—"),
            ("note", "Napomena", getattr(appointment, "note", "") or "—"),
        ]
        for i, (icon, field_label, value) in enumerate(rows):
            info.addWidget(self.make_icon_label(icon), i, 0)
            field_key = QLabel(field_label)
            field_key.setObjectName("detailLabel")
            val = QLabel(value)
            val.setObjectName("detailValue")
            val.setWordWrap(True)
            info.addWidget(field_key, i, 1)
            info.addWidget(val, i, 2)

        # DESNO — status + akcije
        status_title = QLabel("Status termina")
        status_title.setObjectName("detailSection")
        self._right.addWidget(status_title)

        status_key = _status_key(appointment)
        symbol, color, label = STATUS_META[status_key]
        self.status_badge = QLabel(f"{symbol}  {label}")
        self.status_badge.setObjectName("statusHighlight")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setStyleSheet(
            f"color: {color}; background-color: {_STATUS_BG[status_key]}; "
            f"border: 1px solid {color}; border-radius: 7px; "
            "padding: 10px; font-size: 14px; font-weight: 700;"
        )
        self._right.addWidget(self.status_badge)

        terminal = status_key in {"completed", "cancelled"}
        if not terminal:
            self._add_section("Dostupne akcije")
            if status_key != "confirmed":
                self._add_action("Potvrdi termin", "confirm", "neutral")
            if getattr(appointment, "arrived_at", None) is None:
                self._add_action("Pacijent je stigao", "arrived", "neutral")
            self._add_action("Označi kao završen", "completed", "neutral")
            self._add_action("Označi 'nije došao'", "no_show", "neutral")

            self._add_section("Operativne akcije")
            self._add_action("Uredi termin", "edit", "teal")
            self._add_action("Pomjeri termin", "move", "teal")
            self._add_action("Otkaži termin", "cancel", "danger")

        columns.addLayout(info, 2)
        columns.addLayout(self._right, 1)
        self.body_layout().addLayout(columns)

        # "Izbriši termin" — dostupno za SVE statuse (uključujući
        # terminalne, za razliku od gornjih uslovnih akcija), vizuelno
        # najudaljenije/najupadljivije destruktivno dugme, van "Otkaži"
        # (Faza F, HIGH — hard delete, odvojeno od cancel-a).
        self.body_layout().addSpacing(6)
        delete_button = QPushButton("Izbriši termin")
        delete_button.setObjectName("deleteFromDetailsButton")
        delete_button.clicked.connect(lambda: self._choose("delete"))
        self.body_layout().addWidget(delete_button)
        self._action_buttons.append(delete_button)

        self.add_secondary_button("Zatvori")
        self._apply_style()

    def _add_section(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("detailSection")
        self._right.addWidget(label)

    def _add_action(self, label: str, action: str, kind: str = "neutral") -> None:
        button = QPushButton(label)
        if kind == "teal":
            button.setObjectName("outlineTealButton")
        elif kind == "danger":
            button.setObjectName("outlineDangerButton")
        else:
            button.setObjectName("detailActionButton")
        button.clicked.connect(lambda: self._choose(action))
        self._right.addWidget(button)
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
        super()._apply_style()
        self.setStyleSheet(
            self.styleSheet()
            + """
            #detailLabel { color: #718096; font-weight: 600; font-size: 12px; }
            #detailValue { color: #10213d; }
            #detailSection {
                color: #31578a; font-weight: 700; margin-top: 6px;
            }
            #detailActionButton {
                background-color: #ffffff; color: #10213d;
                border: 1px solid #cad8e2; border-radius: 6px;
                min-height: 34px; padding: 2px 12px; text-align: left;
            }
            #detailActionButton:hover { background-color: #eef8f9; border-color: #078f96; }
            #deleteFromDetailsButton {
                background-color: #ffffff; color: #ef334f;
                border: 1px solid #f5c6cb; border-radius: 6px;
                min-height: 34px; padding: 2px 12px; font-weight: 600;
            }
            #deleteFromDetailsButton:hover {
                background-color: #ef334f; color: #ffffff; border-color: #ef334f;
            }
            """
        )
