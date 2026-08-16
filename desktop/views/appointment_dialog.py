"""Dijalog za unos novog termina (Faza 0 — staff-facing unos)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class AppointmentDialog(QDialog):
    """Skuplja ime/telefon/email/uslugu/napomenu — bez validacije.

    Namjerno nema validacije: Faza 0 sveska je slobodna forma, napomena je
    slobodan tekst, a ništa ne smije da "smeta" pri brzom unosu.
    """

    def __init__(self, services: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novi termin")

        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.service_combo = QComboBox()
        self.service_combo.addItems(services)
        self.note_edit = QPlainTextEdit()

        form = QFormLayout()
        form.addRow("Ime i prezime:", self.name_edit)
        form.addRow("Telefon:", self.phone_edit)
        form.addRow("Email:", self.email_edit)
        form.addRow("Usluga:", self.service_combo)
        form.addRow("Napomena:", self.note_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_data(self) -> dict[str, str]:
        return {
            "patient_name": self.name_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "service": self.service_combo.currentText(),
            "note": self.note_edit.toPlainText(),
        }
