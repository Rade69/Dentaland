"""Dnevni prikaz kalendara — doktori kao kolone (Faza E redizajna).

Zaseban widget (ne mega-WeekView): kolone = doktori, redovi = vremenski
slotovi za izabrani datum. Dijeli male stabilne helpere iz ``week_view``
(status/boje). Isti click/context model kao WeekView — lijevi klik na termin
emituje ``appointment_clicked``, desni klik daje status-aware brze akcije,
prazan slot emituje ``slot_selected``. Drag&drop ostaje WeekView-specific.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMenu,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from dentaland.services import AppointmentDTO
from desktop.fake_data import SARAJEVO
from desktop.views.week_view import STATUS_META, WeekView, _status_key, status_icon

_APPT_ID_ROLE = Qt.ItemDataRole.UserRole
_BLOCK_ROLE = Qt.ItemDataRole.UserRole + 1

DAY_START_HOUR = 8
DAY_END_HOUR = 20
SLOT_MINUTES = 60
CLICK_MINUTES = 30


class DayView(QTableWidget):
    """Jedan dan, doktori kao kolone."""

    slot_selected = Signal(object)  # datetime početka praznog slota
    appointment_clicked = Signal(int)  # klik na termin -> Detalji
    appointment_action_requested = Signal(int, str)  # akcija iz kontekst menija

    def __init__(self, store: Any, day: date, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = store
        self.day = day
        self._pending_click_minutes = 0
        self._doctor_ids: list[int] = []
        self._doctor_names: dict[int, str] = {}

        doctors = self._fetch_doctors()
        self._doctor_ids = [doctor.id for doctor in doctors]
        self._doctor_names = {doctor.id: doctor.ime for doctor in doctors}

        rows = int((DAY_END_HOUR - DAY_START_HOUR) * 60 / SLOT_MINUTES)
        self.setRowCount(rows)
        self.setColumnCount(len(self._doctor_ids))
        self.setHorizontalHeaderLabels([self._doctor_names[d] for d in self._doctor_ids])
        self.setVerticalHeaderLabels(
            [self._format_minutes(DAY_START_HOUR * 60 + i * SLOT_MINUTES) for i in range(rows)]
        )

        self.horizontalHeader().setStretchLastSection(True)
        for column in range(self.columnCount()):
            self.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Stretch
            )
        self.verticalHeader().setMinimumSectionSize(20)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setFixedWidth(64)
        self.verticalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.horizontalHeader().setFixedHeight(46)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.setMinimumHeight(300)
        self.setWordWrap(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self.cellClicked.connect(self._on_cell_clicked)
        self.refresh()

    def set_day(self, day: date) -> None:
        self.day = day
        self.refresh()

    @staticmethod
    def _format_minutes(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _fetch_doctors(self) -> list[Any]:
        doctors_fn = getattr(self.store, "doctors", None)
        return list(doctors_fn()) if callable(doctors_fn) else []

    def _fetch_appointments(self) -> list[AppointmentDTO]:
        fetch = getattr(self.store, "all_combined", None)
        if not callable(fetch):
            return []
        return [
            appt
            for appt in fetch()
            if appt.start.astimezone(SARAJEVO).date() == self.day
        ]

    def _fetch_blocks(self) -> list:
        week_start = self.day - timedelta(days=self.day.weekday())
        blocks: list = []
        for method_name in ("time_off_for_week", "breaks_for_week"):
            method = getattr(self.store, method_name, None)
            if not callable(method):
                continue
            for block in method(week_start):
                if block.start.astimezone(SARAJEVO).date() == self.day:
                    blocks.append(block)
        return blocks

    def _slot_datetime(self, row: int, extra_minutes: int = 0) -> datetime:
        minutes = DAY_START_HOUR * 60 + row * SLOT_MINUTES + extra_minutes
        return datetime(
            self.day.year, self.day.month, self.day.day,
            minutes // 60, minutes % 60, tzinfo=SARAJEVO,
        )

    def _cell_for(self, appt: AppointmentDTO) -> tuple[int, int] | None:
        if appt.doctor_id not in self._doctor_names:
            return None
        col = self._doctor_ids.index(appt.doctor_id)
        local = appt.start.astimezone(SARAJEVO)
        minutes = local.hour * 60 + local.minute
        offset = minutes - DAY_START_HOUR * 60
        if offset < 0:
            return None
        row = offset // SLOT_MINUTES
        if row >= self.rowCount():
            return None
        return row, col

    def _cell_span(self, appt: AppointmentDTO) -> tuple[tuple[int, int], int] | None:
        cell = self._cell_for(appt)
        if cell is None:
            return None
        row, col = cell
        duration_minutes = (appt.end - appt.start).total_seconds() / 60
        span = max(int((duration_minutes + SLOT_MINUTES - 1) // SLOT_MINUTES), 1)
        return (row, col), min(span, self.rowCount() - row)

    def _block_row_span(self, block: Any) -> tuple[int, int] | None:
        if block.doctor_id not in self._doctor_names:
            return None
        local_start = block.start.astimezone(SARAJEVO)
        local_end = block.end.astimezone(SARAJEVO)
        start_minutes = local_start.hour * 60 + local_start.minute
        end_minutes = local_end.hour * 60 + local_end.minute
        first = DAY_START_HOUR * 60
        last = DAY_END_HOUR * 60
        start_minutes = max(start_minutes, first)
        end_minutes = min(end_minutes, last)
        if end_minutes <= start_minutes:
            return None
        row = max(0, (start_minutes - first) // SLOT_MINUTES)
        span = max(1, math.ceil((end_minutes - start_minutes) / SLOT_MINUTES))
        return row, min(span, self.rowCount() - row)

    def _appointments_by_cell(self) -> dict[tuple[int, int], list[AppointmentDTO]]:
        result: dict[tuple[int, int], list[AppointmentDTO]] = {}
        for appt in self._fetch_appointments():
            span_info = self._cell_span(appt)
            if span_info is None:
                continue
            (row, col), span = span_info
            for r in range(row, row + span):
                result.setdefault((r, col), []).append(appt)
        return result

    def visible_status_counts(self) -> dict[str, int]:
        counts = dict.fromkeys(STATUS_META, 0)
        for appt in self._fetch_appointments():
            counts[_status_key(appt)] += 1
        return counts

    def visible_doctor_counts(self) -> dict[int, int]:
        """Broj vidljivih termina po doktoru za prikazani dan."""
        counts: dict[int, int] = {}
        for appt in self._fetch_appointments():
            if self._cell_span(appt) is None:
                continue
            doctor_id = getattr(appt, "doctor_id", None)
            if doctor_id is None:
                continue
            counts[doctor_id] = counts.get(doctor_id, 0) + 1
        return counts

    def refresh(self) -> None:
        self.clearSpans()
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                old_widget = self.cellWidget(row, col)
                self.removeCellWidget(row, col)
                if old_widget is not None:
                    old_widget.deleteLater()
                item = QTableWidgetItem("")
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.setItem(row, col, item)

        for block in self._fetch_blocks():
            block_span = self._block_row_span(block)
            if block_span is None:
                continue
            row, span = block_span
            col = self._doctor_ids.index(block.doctor_id)
            if span > 1:
                self.setSpan(row, col, span, 1)
            block_item = self.item(row, col)
            assert block_item is not None
            block_item.setText(block.label)
            block_item.setBackground(QColor("#ffffff"))
            block_item.setData(_BLOCK_ROLE, True)
            block_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            block_card = QLabel(block.label)
            block_card.setAlignment(Qt.AlignmentFlag.AlignCenter)
            block_card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            block_card.setStyleSheet(
                "background:#f1f3f5; color:#1f2937; border:1px solid #cfd6dd; "
                "border-radius:7px; margin:5px 9px; padding:5px; font-weight:600;"
            )
            self.setCellWidget(row, col, block_card)

        grouped: dict[tuple[int, int], tuple[int, list[AppointmentDTO]]] = {}
        for appt in self._fetch_appointments():
            span_info = self._cell_span(appt)
            if span_info is None:
                continue
            (row, col), span = span_info
            cur_span, appts = grouped.get((row, col), (0, []))
            grouped[(row, col)] = (max(cur_span, span), appts + [appt])

        for (row, col), (span, appts) in grouped.items():
            if span > 1:
                self.setSpan(row, col, span, 1)
            cell_item = self.item(row, col)
            assert cell_item is not None
            appt = appts[0]
            local_start = appt.start.astimezone(SARAJEVO)
            local_end = appt.end.astimezone(SARAJEVO)
            doctor_index = (
                self._doctor_ids.index(appt.doctor_id)
                if appt.doctor_id in self._doctor_names
                else 0
            )
            background, border, text_color = WeekView._DOCTOR_CARD_PALETTE[
                doctor_index % len(WeekView._DOCTOR_CARD_PALETTE)
            ]
            symbol = status_icon(appt)
            cell_item.setText(
                f"{symbol} {appt.patient_name}\n"
                f"{local_start:%H:%M}–{local_end:%H:%M} · {appt.service}"
            )
            cell_item.setBackground(QColor(background))
            cell_item.setForeground(QColor(text_color))
            cell_item.setData(_APPT_ID_ROLE, appt.id)
            cell_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )

    def _get_appointment(self, appt_id: int) -> Any:
        getter = getattr(self.store, "get", None)
        return getter(appt_id) if callable(getter) else None

    def _add_menu_action(self, menu: QMenu, label: str, appt_id: int, action: str) -> None:
        qaction = menu.addAction(label)
        qaction.triggered.connect(
            lambda: self.appointment_action_requested.emit(appt_id, action)
        )

    def _open_context_menu(self, position: QPoint) -> None:
        item = self.itemAt(position)
        if item is None:
            return
        appt_id = item.data(_APPT_ID_ROLE)
        if appt_id is None:
            return
        appt = self._get_appointment(appt_id)
        status_key = _status_key(appt) if appt is not None else "waiting"
        terminal = status_key in {"completed", "cancelled"}

        menu = QMenu(self)
        self._add_menu_action(menu, "Otvori detalje", appt_id, "open_details")
        if not terminal:
            menu.addSeparator()
            if status_key != "confirmed":
                self._add_menu_action(menu, "Potvrdi termin", appt_id, "confirm")
            already_arrived = getattr(appt, "arrived_at", None) is not None
            if already_arrived:
                self._add_menu_action(menu, "Poništi (nije stiglo)", appt_id, "unarrived")
            else:
                self._add_menu_action(menu, "Pacijent je stigao", appt_id, "arrived")
            self._add_menu_action(menu, "Označi kao završen", appt_id, "completed")
            self._add_menu_action(menu, "Označi 'nije došao'", appt_id, "no_show")
            menu.addSeparator()
            self._add_menu_action(menu, "Uredi termin", appt_id, "edit")
            self._add_menu_action(menu, "Pomjeri termin", appt_id, "move")
            menu.addSeparator()
            self._add_menu_action(menu, "Otkaži termin", appt_id, "cancel")

        # Izbriši termin — dostupno za SVE statuse (uključujući terminalne),
        # vizuelno odvojeno na dnu (Faza F, HIGH — hard delete).
        menu.addSeparator()
        self._add_menu_action(menu, "Izbriši termin", appt_id, "delete")

        menu.exec(self.viewport().mapToGlobal(position))

    def _on_cell_clicked(self, row: int, col: int) -> None:
        appts = self._appointments_by_cell().get((row, col), [])
        if appts:
            self.appointment_clicked.emit(appts[0].id)
            return
        item = self.item(row, col)
        if item is not None and not item.data(_BLOCK_ROLE):
            self.slot_selected.emit(self._slot_datetime(row, self._pending_click_minutes))
