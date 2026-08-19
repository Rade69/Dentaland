"""Obrada online zahtjeva — doktor/vrijeme/usluga + Potvrdi/Odbij (Faza D redizajna).

Jedan jasan workflow za web zahtjev: read-only prikaz pacijenta (ime/telefon/
email/željeni datum) + input (doktor/vrijeme/usluga). Vrijeme je ``QTimeEdit``
(ručni izbor) — NEMA lažnih slot dugmadi dok ne postoji pravi availability
servis (zaključana odluka iz plana). Koristi BaseDialog B2 helpere.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtCore import QTime
from PySide6.QtWidgets import QComboBox, QFormLayout, QGridLayout, QLabel, QTimeEdit, QWidget

from desktop.views.dialogs.base_dialog import BaseDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")


class ProcessRequestDialog(BaseDialog):
    """Odbij/Potvrdi online zahtjev — footer akcije, ``selected_action()`` razlikuje ishod."""

    def __init__(
        self,
        request: Any,
        doctors: list[tuple[int, str]],
        services: list[tuple[int, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Obradi zahtjev", parent, icon="calendar")
        self.request = request
        self._selected_action: str | None = None
        self._doctor_ids = [doctor_id for doctor_id, _name in doctors]
        self._service_ids = [service_id for service_id, _name in services]

        # read-only pacijent info (sa ikonicama)
        info = QGridLayout()
        info.setHorizontalSpacing(8)
        info.setVerticalSpacing(6)
        info.setColumnStretch(1, 1)

        rows = [
            ("user", getattr(request, "ime", "") or "—"),
            ("phone", getattr(request, "telefon", "") or "—"),
        ]
        email = getattr(request, "email", "") or ""
        if email:
            rows.append(("mail", email))
        rows.append(("calendar", f"Željeni datum: {request.requested_date:%d.%m.%Y.}"))

        for i, (icon, text) in enumerate(rows):
            info.addWidget(self.make_icon_label(icon), i, 0)
            value = QLabel(text)
            value.setObjectName("reqMeta")
            value.setWordWrap(True)
            info.addWidget(value, i, 1)
        self.body_layout().addLayout(info)

        # input
        self.doctor_combo = QComboBox()
        self.doctor_combo.addItems([name for _id, name in doctors])

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(9, 0))

        self.service_combo = QComboBox()
        self.service_combo.addItems([name for _id, name in services])

        form = QFormLayout()
        form.addRow("Doktor *", self.doctor_combo)
        form.addRow("Vrijeme *", self.time_edit)
        form.addRow("Usluga *", self.service_combo)
        self.body_layout().addLayout(form)

        # footer: [Odbij zahtjev] [Potvrdi termin]
        reject_button = self.add_footer_button("Odbij zahtjev", "outlineDangerButton")
        reject_button.clicked.connect(lambda: self._choose("reject"))
        confirm_button = self.add_footer_button("Potvrdi termin", "dialogPrimaryButton")
        confirm_button.clicked.connect(lambda: self._choose("confirm"))

    def _choose(self, action: str) -> None:
        self._selected_action = action
        if action == "confirm":
            self.accept()
        else:
            self.reject()

    def selected_action(self) -> str | None:
        return self._selected_action

    def values(self) -> tuple[int, int, datetime]:
        """Vrati ``(doctor_id, service_id, start)`` — start u Europe/Sarajevo."""
        time_val = self.time_edit.time()
        start = datetime(
            self.request.requested_date.year,
            self.request.requested_date.month,
            self.request.requested_date.day,
            time_val.hour(),
            time_val.minute(),
            tzinfo=SARAJEVO,
        )
        return (
            self._doctor_ids[self.doctor_combo.currentIndex()],
            self._service_ids[self.service_combo.currentIndex()],
            start,
        )
