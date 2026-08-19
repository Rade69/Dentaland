"""Otkaži termin — stilizovani modal potvrde (Faza C redizajna).

Bez razloga otkazivanja (šema ga ne čuva). Otkazani termin OSTAIE sačuvan
u istoriji — ovo je cancel, ne hard delete (Faza F, zasebno).
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from desktop.views.dialogs.base_dialog import BaseDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")


class CancelAppointmentDialog(BaseDialog):
    """Potvrda otkazivanja — pacijent + vrijeme + napomena o istoriji."""

    def __init__(self, appointment: Any, parent: QWidget | None = None) -> None:
        super().__init__("Otkaži termin", parent)

        start = appointment.start.astimezone(SARAJEVO)
        end = appointment.end.astimezone(SARAJEVO)

        name = QLabel(getattr(appointment, "patient_name", ""))
        name.setObjectName("cancelPatient")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        when = QLabel(f"{start:%d.%m.%Y.} · {start:%H:%M}–{end:%H:%M}")
        when.setObjectName("cancelWhen")
        when.setAlignment(Qt.AlignmentFlag.AlignCenter)

        note = QLabel("Otkazani termin ostaje sačuvan u istoriji.")
        note.setObjectName("cancelNote")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.body_layout().addWidget(name)
        self.body_layout().addWidget(when)
        self.body_layout().addWidget(note)

        self.add_secondary_button("Odustani")
        cancel_button = self.add_primary_button("Otkaži termin")
        cancel_button.setStyleSheet(
            "background:#ef334f; color:#ffffff; border:1px solid #ef334f; "
            "border-radius:6px; min-height:36px; padding:2px 18px; font-weight:600;"
        )
        self.setStyleSheet(
            self.styleSheet()
            + """
            #cancelPatient { color: #10213d; font-size: 15px; font-weight: 700; }
            #cancelWhen { color: #42526b; font-size: 13px; }
            #cancelNote { color: #718096; font-size: 12px; }
            """
        )
