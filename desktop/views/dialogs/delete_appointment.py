"""Izbriši termin — destruktivni confirm modal (Faza F redizajna, HIGH).

Hard delete je nepovratan i odvojen od "Otkaži termin" (Faza C — otkazan
termin ostaje sačuvan u istoriji). Namjerno bez razloga brisanja (isti
princip minimizacije kao Cancel — nema šematskog mjesta da se sačuva).

Enter NE aktivira brisanje — dugme je eksplicitno isključeno iz
autoDefault/default ponašanja koje ``BaseDialog.add_primary_button``
inače ne sprečava, jer je ovo jedina destruktivna, nepovratna akcija u
cijelom redizajnu koja to zahtijeva.
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from desktop.views.dialogs.base_dialog import BaseDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")


class DeleteAppointmentDialog(BaseDialog):
    """Potvrda trajnog brisanja — pacijent + vrijeme + eksplicitno upozorenje."""

    def __init__(self, appointment: Any, parent: QWidget | None = None) -> None:
        super().__init__("Izbriši termin", parent, icon="alert")

        start = appointment.start.astimezone(SARAJEVO)
        end = appointment.end.astimezone(SARAJEVO)

        warn_row = QHBoxLayout()
        warn_row.addStretch()
        warn_row.addWidget(self.make_icon_label("alert", "#ef334f", 20))
        warn_row.addStretch()
        self.body_layout().addLayout(warn_row)

        headline = QLabel("Ova radnja trajno uklanja termin:")
        headline.setObjectName("deleteHeadline")
        headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        headline.setWordWrap(True)

        name = QLabel(getattr(appointment, "patient_name", ""))
        name.setObjectName("deletePatient")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        when = QLabel(f"{start:%d.%m.%Y.} · {start:%H:%M}–{end:%H:%M}")
        when.setObjectName("deleteWhen")
        when.setAlignment(Qt.AlignmentFlag.AlignCenter)

        note = QLabel(
            'Ako pacijent samo otkazuje termin, koristite "Otkaži termin".'
        )
        note.setObjectName("deleteNote")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note_box = QFrame()
        note_box.setObjectName("deleteNoteBox")
        note_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        note_box.setStyleSheet(
            "background-color: #fdecef; border: 1px solid #f5c6cb; border-radius: 6px;"
        )
        note_box_layout = QVBoxLayout(note_box)
        note_box_layout.setContentsMargins(12, 8, 12, 8)
        note_box_layout.addWidget(note)

        self.body_layout().addWidget(headline)
        self.body_layout().addWidget(name)
        self.body_layout().addWidget(when)
        self.body_layout().addWidget(note_box)

        self.add_secondary_button("Odustani")
        delete_button = self.add_primary_button("Izbriši termin")
        delete_button.setObjectName("deletePrimaryButton")
        # Namjerno: Enter ne smije aktivirati brisanje (jedina nepovratna
        # akcija u redizajnu koja to zahtijeva — vidi modul docstring).
        delete_button.setAutoDefault(False)
        delete_button.setDefault(False)
        delete_button.setStyleSheet(
            "background:#ef334f; color:#ffffff; border:1px solid #ef334f; "
            "border-radius:6px; min-height:36px; padding:2px 18px; font-weight:600;"
        )

        self.setStyleSheet(
            self.styleSheet()
            + """
            #deleteHeadline { color: #10213d; font-size: 13px; font-weight: 600; }
            #deletePatient { color: #10213d; font-size: 15px; font-weight: 700; }
            #deleteWhen { color: #42526b; font-size: 13px; }
            #deleteNote { color: #a12a3a; font-size: 12px; }
            """
        )
