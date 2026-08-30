"""Desni dashboard paneli: novi, nepotvrđeni i današnji otkazani termini."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dentaland.services.requests import OverlapError  # noqa: F401  # re-eksport (REF-01 contract)
from dentaland.timezone import SARAJEVO
from desktop.controllers.appointment_controller import AppointmentController
from desktop.controllers.request_controller import RequestController
from desktop.views.sidebar import svg_icon


class DashboardPanels(QScrollArea):
    changed = Signal()

    def __init__(self, store: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._request_controller = RequestController(store)
        self._appointment_controller = AppointmentController(
            store, self, self._on_appointment_changed
        )
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
        for box, tone in (
            (self.pending_box, "info"),
            (self.awaiting_box, "warning"),
            (self.cancelled_box, "danger"),
        ):
            box.setObjectName("dashboardBox")
            box.setProperty("tone", tone)
        today_title = QLabel("DANAS – Sažetak")
        today_title.setObjectName("dashboardSectionTitle")
        self.content_layout.addWidget(today_title)
        self.content_layout.addWidget(self.pending_box)
        self.content_layout.addWidget(self.awaiting_box)
        self.content_layout.addWidget(self.cancelled_box)
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
        self.pending_box.setTitle("")
        layout = self._replace_layout(self.pending_box)
        self._add_card_header(layout, "Novi zahtjevi", len(rows), "calendar", "#078f96")
        if not rows:
            layout.addWidget(QLabel("Sve je obrađeno."))
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
            process = QPushButton("Obradi")
            process.setObjectName("processButton")
            process.clicked.connect(lambda _checked=False, item=request: self._confirm(item))
            row_layout.addWidget(process)
            layout.addWidget(row)

    def _fill_appointments(
        self, box: QGroupBox, title: str, rows: list, *, confirmable: bool = False
    ) -> None:
        box.setTitle("")
        layout = self._replace_layout(box)
        if box is self.awaiting_box:
            self._add_card_header(layout, title, len(rows), "clock", "#d39400")
        else:
            self._add_card_header(layout, title, len(rows), "hourglass", "#ef334f")
        if not rows:
            layout.addWidget(QLabel("Nema stavki"))
            return
        for appt in rows:
            local = appt.start.astimezone(SARAJEVO)
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
                cancel = QPushButton("Odbaci")
                cancel.setObjectName("rejectButton")
                cancel.clicked.connect(
                    lambda _checked=False, item=appt: self._cancel_scheduled(item.id)
                )
                row_layout.addWidget(cancel)
            layout.addWidget(row)

    @staticmethod
    def _add_card_header(
        layout: QVBoxLayout,
        title: str,
        count: int,
        icon_name: str,
        color: str,
    ) -> None:
        header = QWidget()
        header.setObjectName("dashboardCardHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 2)
        header_layout.setSpacing(8)

        icon = QLabel()
        icon.setObjectName("dashboardCardIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(30, 30)
        icon.setPixmap(svg_icon(icon_name, color, 23).pixmap(23, 23))

        name = QLabel(title)
        name.setObjectName("dashboardCardTitle")
        number = QLabel(str(count))
        number.setObjectName("dashboardCardCount")
        number.setProperty("toneColor", color)
        number.setStyleSheet(f"color: {color};")
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(icon)
        header_layout.addWidget(name, 1)
        header_layout.addWidget(number)
        layout.addWidget(header)

    def _confirm_scheduled(self, appt_id: int) -> None:
        self._appointment_controller.handle_appointment_action(appt_id, "confirm")

    def _cancel_scheduled(self, appt_id: int) -> None:
        self._appointment_controller.handle_appointment_action(appt_id, "reject")

    def _on_appointment_changed(self) -> None:
        self.refresh()
        self.changed.emit()

    def _confirm(self, request: Any) -> None:
        if self._request_controller.process_pending_request(request, self) is None:
            return
        self.refresh()
        self.changed.emit()
