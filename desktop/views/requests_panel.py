"""Desni dashboard paneli: novi, nepotvrđeni i današnji otkazani termini."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, cast
from zoneinfo import ZoneInfo

from PySide6.QtCore import QDate, QDateTime, Qt, QTime, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class ConfirmationDialog(QDialog):
    """Osoblje bira stvarnog doktora, uslugu i vrijeme prije potvrde."""

    def __init__(
        self,
        request: Any,
        doctors: list[Any],
        services: list[tuple[int, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Potvrdi zahtjev")
        self._doctor_ids = [int(doctor.id) for doctor in doctors]
        self._service_ids = [service_id for service_id, _name in services]
        self.doctor = QComboBox()
        self.doctor.addItems([doctor.ime for doctor in doctors])
        self.service = QComboBox()
        self.service.addItems([name for _service_id, name in services])
        self.start = QDateTimeEdit()
        zone = ZoneInfo("Europe/Sarajevo")
        initial = datetime.combine(request.requested_date, time(9), tzinfo=zone)
        self.start.setDateTime(
            QDateTime(
                QDate(initial.year, initial.month, initial.day),
                QTime(initial.hour, initial.minute),
            )
        )
        self.start.setCalendarPopup(True)
        form = QFormLayout()
        form.addRow("Doktor", self.doctor)
        form.addRow("Usluga", self.service)
        form.addRow("Datum i vrijeme", self.start)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[int, int, datetime]:
        start = cast(datetime, self.start.dateTime().toPython())
        if start.tzinfo is None:
            start = start.replace(tzinfo=ZoneInfo("Europe/Sarajevo"))
        return (
            self._doctor_ids[self.doctor.currentIndex()],
            self._service_ids[self.service.currentIndex()],
            start,
        )


class DashboardPanels(QScrollArea):
    changed = Signal()

    def __init__(self, store: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.setObjectName("dashboardPanels")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(255)
        self.setMaximumWidth(285)
        container = QWidget()
        container.setObjectName("dashboardPanelContent")
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        self.pending_box = QGroupBox()
        self.awaiting_box = QGroupBox()
        self.cancelled_box = QGroupBox()
        self.next_free_box = QGroupBox("Sljedeći slobodan termin")
        for box in (
            self.pending_box,
            self.awaiting_box,
            self.cancelled_box,
            self.next_free_box,
        ):
            box.setObjectName("dashboardBox")
        self.content_layout.addWidget(self.pending_box)
        self.content_layout.addWidget(self.awaiting_box)
        self.content_layout.addWidget(self.cancelled_box)
        next_free_layout = QVBoxLayout(self.next_free_box)
        next_free_layout.setSpacing(5)
        next_free = QLabel("Pretraga prvog slobodnog termina\nbiće dostupna uskoro.")
        next_free.setObjectName("nextFreePlaceholder")
        next_free.setWordWrap(True)
        next_free_layout.addWidget(next_free)
        make_button = QPushButton("Napravi termin")
        make_button.setEnabled(False)
        make_button.setToolTip("Pretraga slobodnih termina biće dodana zasebno")
        next_free_layout.addWidget(make_button)
        self.content_layout.addWidget(self.next_free_box)
        self.content_layout.addStretch()
        self.setWidget(container)
        self.refresh()

    def refresh(self) -> None:
        pending = self._call("pending_requests")
        awaiting = self._call("awaiting_confirmation")
        cancelled = self._call("cancelled_today")
        self._fill_pending(pending)
        self._fill_appointments(self.awaiting_box, "Čekaju potvrdu", awaiting, confirmable=True)
        self._fill_appointments(self.cancelled_box, "Otkazani danas", cancelled)

    def _call(self, name: str) -> list:
        method = getattr(self.store, name, None)
        return list(method()) if callable(method) else []

    @staticmethod
    def _replace_layout(box: QGroupBox) -> QVBoxLayout:
        old = box.layout()
        if old is None:
            layout = QVBoxLayout()
            box.setLayout(layout)
            return layout
        while old.count():
            item = old.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        assert isinstance(old, QVBoxLayout)
        return old

    def _fill_pending(self, rows: list) -> None:
        self.pending_box.setTitle(f"Novi zahtjevi ({len(rows)})")
        layout = self._replace_layout(self.pending_box)
        if not rows:
            layout.addWidget(QLabel("Nema novih zahtjeva"))
            return
        for request in rows:
            row = QWidget()
            row.setObjectName("requestRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 3, 0, 3)
            row_layout.setSpacing(5)
            details = QLabel(
                f"<b>{request.ime}</b><br>"
                f"<span style='color:#31578a'>{request.requested_date:%d.%m.%Y.}</span>"
            )
            row_layout.addWidget(details, 1)
            actions = QHBoxLayout()
            actions.setSpacing(4)
            confirm = QPushButton("Potvrdi")
            confirm.setObjectName("confirmButton")
            reject = QPushButton("Odbij")
            reject.setObjectName("rejectButton")
            confirm.clicked.connect(lambda _checked=False, item=request: self._confirm(item))
            reject.clicked.connect(lambda _checked=False, item=request: self._reject(item.id))
            actions.addWidget(confirm)
            actions.addWidget(reject)
            row_layout.addLayout(actions)
            layout.addWidget(row)

    def _fill_appointments(
        self, box: QGroupBox, title: str, rows: list, *, confirmable: bool = False
    ) -> None:
        box.setTitle(f"{title} ({len(rows)})")
        layout = self._replace_layout(box)
        if not rows:
            layout.addWidget(QLabel("Nema stavki"))
            return
        for appt in rows:
            local = appt.start.astimezone(ZoneInfo("Europe/Sarajevo"))
            row = QWidget()
            row.setObjectName("dashboardListItem")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(5)
            details = QLabel(
                f"<b>{appt.patient_name}</b><br>"
                f"<span style='color:#31578a'>{local:%d.%m. u %H:%M} · {appt.service}</span>"
            )
            row_layout.addWidget(details, 1)
            if confirmable:
                confirm = QPushButton("Potvrdi")
                confirm.setObjectName("confirmButton")
                confirm.clicked.connect(
                    lambda _checked=False, item=appt: self._confirm_scheduled(item.id)
                )
                row_layout.addWidget(confirm)
            layout.addWidget(row)

    def _confirm_scheduled(self, appt_id: int) -> None:
        self.store.mark_confirmed(appt_id)
        self.refresh()
        self.changed.emit()

    def _confirm(self, request: Any) -> None:
        doctors = self._call("doctors")
        services = self._call("service_choices")
        if not doctors or not services:
            return
        dialog = ConfirmationDialog(request, doctors, services, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        doctor_id, service_id, start = dialog.values()
        self.store.confirm_pending(request.id, doctor_id, service_id, start)
        self.refresh()
        self.changed.emit()

    def _reject(self, request_id: int) -> None:
        self.store.reject_pending(request_id)
        self.refresh()
        self.changed.emit()
