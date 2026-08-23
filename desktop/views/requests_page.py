"""Dedicated desktop stranica za obradu novih online zahtjeva."""

from __future__ import annotations

from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from desktop.views.requests_panel import process_pending_request

SARAJEVO = ZoneInfo("Europe/Sarajevo")


def _initials(name: str) -> str:
    parts = [part for part in name.split() if part]
    return "".join(part[0].upper() for part in parts[:2]) or "?"


def _sent_text(created_at: Any, today: date | None = None) -> str:
    local = created_at.astimezone(SARAJEVO)
    current = today or date.today()
    if local.date() == current:
        return f"Poslano: danas u {local:%H:%M}"
    return f"Poslano: {local:%d.%m.%Y. u %H:%M}"


class RequestsPage(QWidget):
    """Puni pregled pending zahtjeva sa postojećim dialog tokom obrade."""

    changed = Signal()

    def __init__(self, store: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.setObjectName("requestsPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(14)

        title = QLabel("Novi zahtjevi")
        title.setObjectName("requestsPageTitle")
        subtitle = QLabel("Zahtjevi poslani putem online forme")
        subtitle.setObjectName("requestsPageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.summary = QFrame()
        self.summary.setObjectName("requestsSummary")
        summary_layout = QHBoxLayout(self.summary)
        summary_layout.setContentsMargins(18, 14, 20, 14)
        summary_layout.setSpacing(16)

        summary_icon = QLabel("▤")
        summary_icon.setObjectName("requestsSummaryIcon")
        summary_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_icon.setFixedSize(50, 50)
        summary_layout.addWidget(summary_icon)

        summary_copy = QVBoxLayout()
        summary_copy.setSpacing(4)
        self.count_label = QLabel()
        self.count_label.setObjectName("requestsCount")
        summary_text = QLabel("Obradite zahtjeve što prije kako biste potvrdili termine.")
        summary_text.setObjectName("requestsSummaryText")
        summary_copy.addWidget(self.count_label)
        summary_copy.addWidget(summary_text)
        summary_layout.addLayout(summary_copy, 1)

        summary_art = QLabel("✉  ●")
        summary_art.setObjectName("requestsSummaryArt")
        summary_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_art.setFixedWidth(150)
        summary_layout.addWidget(summary_art)
        root.addWidget(self.summary)

        self.requests_scroll = QScrollArea()
        self.requests_scroll.setObjectName("requestsScroll")
        self.requests_scroll.setWidgetResizable(True)
        self.requests_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.requests_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        container = QWidget()
        container.setObjectName("requestsList")
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.requests_scroll.setWidget(container)
        root.addWidget(self.requests_scroll, 1)

        tip = QFrame()
        tip.setObjectName("requestsTip")
        tip_layout = QHBoxLayout(tip)
        tip_layout.setContentsMargins(18, 10, 18, 10)
        tip_layout.setSpacing(14)
        tip_icon = QLabel("i")
        tip_icon.setObjectName("requestsTipIcon")
        tip_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_icon.setFixedSize(32, 32)
        tip_layout.addWidget(tip_icon)
        tip_copy = QVBoxLayout()
        tip_copy.setSpacing(1)
        tip_title = QLabel("Savjet")
        tip_title.setObjectName("requestsTipTitle")
        tip_text = QLabel(
            "Nakon obrade zahtjeva, pacijent će dobiti e-mail potvrdu o zakazanom terminu."
        )
        tip_text.setObjectName("requestsTipText")
        tip_copy.addWidget(tip_title)
        tip_copy.addWidget(tip_text)
        tip_layout.addLayout(tip_copy, 1)
        root.addWidget(tip)

        self._apply_style()
        self.refresh()

    def refresh(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        method = getattr(self.store, "pending_requests", None)
        requests = list(method()) if callable(method) else []
        count_text = (
            "1 neobrađen zahtjev"
            if len(requests) == 1
            else f"{len(requests)} neobrađena zahtjeva"
        )
        self.count_label.setText(count_text)
        if not requests:
            empty = QFrame()
            empty.setObjectName("requestsEmptyCard")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(20, 24, 20, 24)
            empty_title = QLabel("Sve je obrađeno.")
            empty_title.setObjectName("requestsEmptyTitle")
            empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_text = QLabel("Novi zahtjevi poslani online formom pojaviće se ovdje.")
            empty_text.setObjectName("requestsEmptyText")
            empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(empty_title)
            empty_layout.addWidget(empty_text)
            self.list_layout.addWidget(empty)
            self.list_layout.addStretch()
            return

        for request in requests:
            self.list_layout.addWidget(self._request_row(request))
        self.list_layout.addStretch()

    def _request_row(self, request: Any) -> QWidget:
        row = QFrame()
        row.setObjectName("requestPageRow")
        row.setMinimumHeight(100)
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 13, 18, 13)
        layout.setSpacing(16)

        avatar = QLabel(_initials(request.ime))
        avatar.setObjectName("requestInitials")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(58, 58)
        layout.addWidget(avatar)

        details = QVBoxLayout()
        details.setSpacing(6)
        name = QLabel(request.ime)
        name.setObjectName("requestName")
        details.addWidget(name)

        contact_row = QHBoxLayout()
        contact_row.setSpacing(18)
        phone = QLabel(f"☎  {request.telefon or 'Telefon nije naveden'}")
        phone.setObjectName("requestPhone")
        email = QLabel(f"✉  {request.email or 'E-mail nije naveden'}")
        email.setObjectName("requestEmail")
        contact_row.addWidget(phone)
        contact_row.addWidget(email)
        contact_row.addStretch()
        details.addLayout(contact_row)

        metadata = QHBoxLayout()
        metadata.setSpacing(28)
        requested = QLabel(f"▣  Traženi datum: {request.requested_date:%d.%m.%Y.}")
        requested.setObjectName("requestDate")
        created = QLabel(f"◷  {_sent_text(request.created_at)}")
        created.setObjectName("requestCreatedAt")
        metadata.addWidget(requested)
        metadata.addWidget(created)
        metadata.addStretch()
        details.addLayout(metadata)
        layout.addLayout(details, 1)

        status = QLabel("NOVO")
        status.setObjectName("requestNewBadge")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setFixedSize(54, 28)
        layout.addWidget(status)

        process = QPushButton("Obradi")
        process.setObjectName("processRequestButton")
        process.setFixedSize(98, 42)
        process.clicked.connect(lambda _checked=False, item=request: self._process(item))
        layout.addWidget(process)

        more = QLabel("⋮")
        more.setObjectName("requestMore")
        more.setAlignment(Qt.AlignmentFlag.AlignCenter)
        more.setFixedWidth(18)
        layout.addWidget(more)
        return row

    def _process(self, request: Any) -> None:
        if process_pending_request(self.store, request, self):
            self.refresh()
            self.changed.emit()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #requestsPage {
                background-color: #ffffff; color: #10213d;
                font-family: "Segoe UI"; font-size: 13px;
            }
            #requestsPageTitle { color: #10213d; font-size: 26px; font-weight: 700; }
            #requestsPageSubtitle { color: #6d87a8; font-size: 14px; }
            #requestsSummary, #requestsTip, #requestPageRow, #requestsEmptyCard {
                background-color: #ffffff; border: 1px solid #d9e3ea; border-radius: 10px;
            }
            #requestsSummary { min-height: 78px; }
            #requestsSummaryIcon {
                color: #078f96; background-color: #eefafa;
                border: 1px solid #69c7c7; border-radius: 25px;
                font-size: 26px; font-weight: 500;
            }
            #requestsCount { color: #078f96; font-size: 15px; font-weight: 700; }
            #requestsSummaryText { color: #294767; font-size: 13px; }
            #requestsSummaryArt {
                color: #24aab0; background-color: #e6f6f5;
                border-radius: 10px; font-size: 26px; font-weight: 700;
            }
            #requestsScroll, #requestsList,
            #requestsScroll > QWidget > QWidget { background-color: #ffffff; }
            #requestPageRow { min-height: 100px; }
            #requestInitials {
                color: #078f96; background-color: #e4f4f3;
                border-radius: 29px; font-size: 21px; font-weight: 500;
            }
            #requestName { color: #10213d; font-size: 17px; font-weight: 700; }
            #requestPhone, #requestEmail, #requestDate, #requestCreatedAt {
                color: #294767; font-size: 13px;
            }
            #requestNewBadge {
                color: #078f96; background-color: #e1f4f2;
                border-radius: 5px; font-size: 12px;
            }
            #processRequestButton {
                color: #ffffff; background-color: #078f96;
                border: 1px solid #078f96; border-radius: 7px;
                font-size: 14px; font-weight: 700;
            }
            #processRequestButton:hover { background-color: #087b82; }
            #requestMore { color: #31578a; font-size: 24px; font-weight: 700; }
            #requestsTip { min-height: 62px; background-color: #fbfdfe; }
            #requestsTipIcon {
                color: #078f96; border: 2px solid #078f96;
                border-radius: 16px; font-size: 18px; font-weight: 700;
            }
            #requestsTipTitle { color: #294767; font-size: 13px; font-weight: 700; }
            #requestsTipText, #requestsEmptyText { color: #5d7696; font-size: 12px; }
            #requestsEmptyTitle { color: #10213d; font-size: 16px; font-weight: 700; }
            """
        )
