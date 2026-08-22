"""Obriši blokadu — destruktivni confirm modal (FIX-06).

Blokada (odsustvo/pauza) se lako ponovo kreira, pa za razliku od
``DeleteAppointmentDialog`` (hard delete termina) nema Enter-safety
izuzetka — standardno ``BaseDialog`` Enter-na-primarno ponašanje je u redu.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from desktop.fake_data import SARAJEVO
from desktop.views.dialogs.base_dialog import BaseDialog


class BlockoutDeleteConfirmDialog(BaseDialog):
    """Potvrda brisanja blokade — doktor + vrijeme + razlog."""

    def __init__(self, block: Any, parent: QWidget | None = None) -> None:
        super().__init__("Obriši blokadu", parent, icon="alert")

        start = block.start.astimezone(SARAJEVO)
        end = block.end.astimezone(SARAJEVO)

        warn_row = QHBoxLayout()
        warn_row.addStretch()
        warn_row.addWidget(self.make_icon_label("alert", "#ef334f", 20))
        warn_row.addStretch()
        self.body_layout().addLayout(warn_row)

        headline = QLabel("Ova radnja uklanja blokadu:")
        headline.setObjectName("deleteHeadline")
        headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        headline.setWordWrap(True)

        doctor = QLabel(getattr(block, "doctor_name", ""))
        doctor.setObjectName("deletePatient")
        doctor.setAlignment(Qt.AlignmentFlag.AlignCenter)

        when = QLabel(f"{start:%d.%m.%Y.} · {start:%H:%M}–{end:%H:%M}")
        when.setObjectName("deleteWhen")
        when.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.body_layout().addWidget(headline)
        self.body_layout().addWidget(doctor)
        self.body_layout().addWidget(when)

        reason = getattr(block, "reason", "") or ""
        if reason:
            reason_label = QLabel(f"Razlog: {reason}")
            reason_label.setObjectName("deleteNote")
            reason_label.setWordWrap(True)
            reason_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.body_layout().addWidget(reason_label)

        self.add_secondary_button("Odustani")
        delete_button = self.add_primary_button("Obriši blokadu")
        delete_button.setObjectName("deletePrimaryButton")
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
