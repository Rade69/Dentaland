"""Dedicated desktop stranica za obradu novih online zahtjeva."""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from desktop.views.requests_panel import process_pending_request

SARAJEVO = ZoneInfo("Europe/Sarajevo")


class RequestsPage(QWidget):
    """Puni pregled pending zahtjeva sa postojećim dialog tokom obrade."""

    changed = Signal()

    def __init__(self, store: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.setObjectName("requestsPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        title = QLabel("Novi zahtjevi")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Zahtjevi poslani putem online forme")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.count_label = QLabel()
        self.count_label.setObjectName("requestsCount")
        root.addWidget(self.count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        container.setObjectName("requestsList")
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)
        self.refresh()

    def refresh(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        method = getattr(self.store, "pending_requests", None)
        requests = list(method()) if callable(method) else []
        self.count_label.setText(f"Neobrađeni zahtjevi: {len(requests)}")
        if not requests:
            empty = QLabel("Sve je obrađeno.")
            empty.setObjectName("requestsEmpty")
            self.list_layout.addWidget(empty)
            self.list_layout.addStretch()
            return

        for request in requests:
            self.list_layout.addWidget(self._request_row(request))
        self.list_layout.addStretch()

    def _request_row(self, request: Any) -> QWidget:
        row = QFrame()
        row.setObjectName("requestPageRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(16)

        details = QVBoxLayout()
        details.setSpacing(4)
        name = QLabel(request.ime)
        name.setObjectName("requestName")
        details.addWidget(name)

        contacts = [value for value in (request.telefon, request.email) if value]
        contact = QLabel(" · ".join(contacts) if contacts else "Kontakt nije naveden")
        contact.setObjectName("requestContact")
        details.addWidget(contact)

        requested = QLabel(f"Traženi datum: {request.requested_date:%d.%m.%Y.}")
        requested.setObjectName("requestDate")
        details.addWidget(requested)

        created = request.created_at.astimezone(SARAJEVO)
        created_label = QLabel(f"Poslano: {created:%d.%m.%Y. u %H:%M}")
        created_label.setObjectName("requestCreatedAt")
        details.addWidget(created_label)
        layout.addLayout(details, 1)

        process = QPushButton("Obradi")
        process.setObjectName("processRequestButton")
        process.clicked.connect(lambda _checked=False, item=request: self._process(item))
        layout.addWidget(process)
        return row

    def _process(self, request: Any) -> None:
        if process_pending_request(self.store, request, self):
            self.refresh()
            self.changed.emit()
