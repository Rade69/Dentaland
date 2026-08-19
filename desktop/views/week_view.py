"""Sedmični prikaz kalendara — početni ekran desktop aplikacije.

Prikazuje 7 dana (ponedjeljak–nedjelja) kao mrežu vremenskih slotova.
Podržava termine više doktora istovremeno, boja-kodirano po doktoru, i
filtriranje po jednom doktoru (``set_filter``). Termini duži od jednog slota
su vertikalno spojeni (``setSpan``) preko svih ćelija koje pokrivaju. Klik na
prazan slot emituje ``slot_selected`` (otvara dijalog za unos); prevlačenje
zauzetog slota mijenja vrijeme termina — overlap provjerava servisni sloj
(``OverlapError``).
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QDropEvent, QMouseEvent
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

from dentaland.services import AppointmentDTO, OverlapError
from desktop.fake_data import SARAJEVO

_APPT_ID_ROLE = Qt.ItemDataRole.UserRole
_BLOCK_ROLE = Qt.ItemDataRole.UserRole + 1


# Jedan izvor istine za status simbol/boju/naziv — dijele ga legenda
# (main_window.py), kartica jednog termina i tekstualna lista više termina
# u istoj ćeliji, da simboli nikad ne izgube sinhronizaciju.
#
# Namjerno OBIČNI Unicode dingbat/geometrijski simboli (ne slikovni emoji
# poput 🕐/👤/💜) — slikovni emoji zahtijevaju posebni font boje (Segoe UI
# Emoji) koji se u malom QLabel HTML tekstu ne mora učitati, pa su znali
# ispasti prazni/nečitljivi. Ovi simboli su i oblikom različiti (ne samo
# bojom) — čitljivo i bez oslanjanja na boju.
STATUS_META: dict[str, tuple[str, str, str]] = {
    "confirmed": ("✓", "#149447", "Potvrđen"),
    "waiting": ("◷", "#ff8a00", "Čeka potvrdu"),
    "arrived": ("▲", "#1473e6", "Stigao"),
    "completed": ("★", "#7c3aed", "Završen"),
    "cancelled": ("✗", "#ef334f", "Otkazan / Nije došao"),
}
STATUS_ORDER = ["confirmed", "waiting", "arrived", "completed", "cancelled"]


def _status_key(appt: AppointmentDTO) -> str:
    status = getattr(getattr(appt, "status", None), "value", None)
    if status in {"CANCELLED", "NO_SHOW"}:
        return "cancelled"
    if status == "COMPLETED":
        return "completed"
    if getattr(appt, "arrived_at", None) is not None:
        return "arrived"
    if getattr(appt, "confirmed_at", None) is not None:
        return "confirmed"
    return "waiting"


def status_icon(appt: AppointmentDTO) -> str:
    """Čisto prezentaciono mapiranje statusnih podataka na ikonicu."""
    return STATUS_META[_status_key(appt)][0]


def _status_visual(appt: AppointmentDTO) -> tuple[str, str]:
    """Simbol i boja za karticu termina — isti izvor kao ``status_icon``."""
    symbol, color, _label = STATUS_META[_status_key(appt)]
    return symbol, color


class WeekView(QTableWidget):
    """Mreža sedmičnog rasporeda (redovi = vrijeme, kolone = dani)."""

    slot_selected = Signal(object)  # datetime početka praznog slota
    appointment_clicked = Signal(int)  # klik na postojeći termin -> Detalji
    appointment_action_requested = Signal(int, str)  # akcija iz kontekst menija
    appointment_moved = Signal(object)  # Appointment koji je pomjeren

    DAY_NAMES = ["Pon", "Uto", "Sri", "Čet", "Pet", "Sub"]
    DAY_COUNT = 6
    DAY_START_HOUR = 8
    DAY_END_HOUR = 20
    SLOT_MINUTES = 60

    _DOCTOR_PALETTE = ["#16a34a", "#f43f5e", "#3b82f6", "#d4a017", "#8b5cf6", "#0891b2"]
    _DOCTOR_CARD_PALETTE = [
        ("#ebf8ed", "#9bd5a4", "#174d26"),
        ("#fff0f2", "#ff9aaa", "#6b1e2c"),
        ("#edf4ff", "#8ab7ff", "#153b73"),
        ("#fff8df", "#e8cb67", "#634c00"),
        ("#f5efff", "#b9a0ef", "#49307d"),
        ("#e9fbff", "#88d9e8", "#15505d"),
    ]

    # Vizuelni red je pun sat (SLOT_MINUTES), ali klik i dalje bira
    # pola sata — gornja/donja polovina ćelije određuje :00 ili :30.
    CLICK_MINUTES = 30

    def __init__(self, store: Any, week_start: date, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = store
        self.week_start = week_start
        self._drag_appt_id: int | None = None
        self._filter_doctor_id: int | None = None
        self._doctor_colors = self._build_doctor_colors()
        self._pending_click_minutes = 0

        rows = int((self.DAY_END_HOUR - self.DAY_START_HOUR) * 60 / self.SLOT_MINUTES)
        self.setRowCount(rows)
        self.setColumnCount(self.DAY_COUNT)
        self.setHorizontalHeaderLabels([
            f"{name}\n{(week_start + timedelta(days=i)).strftime('%d.%m.')}"
            for i, name in enumerate(self.DAY_NAMES)
        ])
        self.setVerticalHeaderLabels([
            self._format_minutes(self.DAY_START_HOUR * 60 + i * self.SLOT_MINUTES)
            for i in range(rows)
        ])
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
        self.verticalHeader().setStyleSheet(
            "QHeaderView::section { padding: 0 8px 0 2px; }"
        )
        self.horizontalHeader().setFixedHeight(46)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.setMinimumHeight(300)
        self.setWordWrap(True)

        # PySide6 stub gap: QTableWidget.DragDrop postoji u runtime-u, ali
        # nedostaje u tip stubovima — ne mijenjati logiku.
        self.setDragDropMode(QTableWidget.DragDrop)  # type: ignore[attr-defined]
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self.cellClicked.connect(self._on_cell_clicked)
        self.refresh()

    # ---- doktori i boje ----

    def _build_doctor_colors(self) -> dict[int, QColor]:
        colors: dict[int, QColor] = {}
        doctors_fn = getattr(self.store, "doctors", None)
        if not callable(doctors_fn):
            return colors
        for i, doctor in enumerate(doctors_fn()):
            colors[doctor.id] = QColor(self._DOCTOR_PALETTE[i % len(self._DOCTOR_PALETTE)])
        return colors

    def set_filter(self, doctor_id: int | None) -> None:
        """Prikaži samo termine datog doktora (``None`` = svi doktori)."""
        self._filter_doctor_id = doctor_id
        self.refresh()

    def set_week_start(self, week_start: date) -> None:
        self.week_start = week_start
        self.setHorizontalHeaderLabels([
            f"{name}\n{(week_start + timedelta(days=i)).strftime('%d.%m.')}"
            for i, name in enumerate(self.DAY_NAMES)
        ])
        self.refresh()

    # ---- mapiranje slot ↔ vrijeme ----

    @staticmethod
    def _format_minutes(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _half_slot_minutes_at(self, y: int, row: int) -> int:
        """Gornja/donja polovina ćelije reda -> 0 ili CLICK_MINUTES.

        Vizuelni red i dalje predstavlja pun sat (SLOT_MINUTES), ali klik
        bira finiju granularnost (CLICK_MINUTES) na osnovu toga gdje
        unutar ćelije korisnik klikne — gornja polovina je puni sat,
        donja polovina je pola sata kasnije.
        """
        row_top = self.rowViewportPosition(row)
        row_height = self.rowHeight(row)
        if row_height <= 0:
            return 0
        fraction = (y - row_top) / row_height
        steps_per_row = max(int(self.SLOT_MINUTES // self.CLICK_MINUTES), 1)
        step = min(int(fraction * steps_per_row), steps_per_row - 1)
        return max(step, 0) * self.CLICK_MINUTES

    def _slot_datetime(self, row: int, col: int, extra_minutes: int = 0) -> datetime:
        day = self.week_start + timedelta(days=col)
        minutes = self.DAY_START_HOUR * 60 + row * self.SLOT_MINUTES + extra_minutes
        return datetime(
            day.year, day.month, day.day,
            minutes // 60, minutes % 60, tzinfo=SARAJEVO,
        )

    def _cell_for(self, appt: AppointmentDTO) -> tuple[int, int] | None:
        local = appt.start.astimezone(SARAJEVO)
        col = (local.date() - self.week_start).days
        if col < 0 or col >= self.DAY_COUNT:
            return None
        minutes = local.hour * 60 + local.minute
        offset = minutes - self.DAY_START_HOUR * 60
        if offset < 0:
            return None
        row = offset // self.SLOT_MINUTES
        if row >= self.rowCount():
            return None
        return row, col

    def _cell_span(self, appt: AppointmentDTO) -> tuple[tuple[int, int], int] | None:
        cell = self._cell_for(appt)
        if cell is None:
            return None
        row, col = cell
        local = appt.start.astimezone(SARAJEVO)
        duration_minutes = (appt.end - appt.start).total_seconds() / 60
        start_minutes = local.hour * 60 + local.minute
        offset_in_slot = (start_minutes - self.DAY_START_HOUR * 60) % self.SLOT_MINUTES
        span = int(math.ceil((offset_in_slot + duration_minutes) / self.SLOT_MINUTES))
        span = max(span, 1)
        return (row, col), min(span, self.rowCount() - row)

    def _fetch_appointments(self) -> list[AppointmentDTO]:
        fetch = getattr(self.store, "all_combined", None)
        if callable(fetch):
            return fetch()
        return self.store.all()

    def _visible_appointments(self) -> list[tuple[tuple[int, int], int, AppointmentDTO]]:
        visible: list[tuple[tuple[int, int], int, AppointmentDTO]] = []
        for appt in self._fetch_appointments():
            appt_doctor = getattr(appt, "doctor_id", None)
            if self._filter_doctor_id is not None and appt_doctor != self._filter_doctor_id:
                continue
            span_info = self._cell_span(appt)
            if span_info is not None:
                cell, span = span_info
                visible.append((cell, span, appt))
        return visible

    def visible_status_counts(self) -> dict[str, int]:
        """Broj termina po statusu, samo za trenutno prikazanu sedmicu (i filter doktora)."""
        counts = dict.fromkeys(STATUS_META, 0)
        for _cell, _span, appt in self._visible_appointments():
            counts[_status_key(appt)] += 1
        return counts

    def _appointments_by_cell(self) -> dict[tuple[int, int], list[AppointmentDTO]]:
        result: dict[tuple[int, int], list[AppointmentDTO]] = {}
        for (row, col), span, appt in self._visible_appointments():
            for r in range(row, row + span):
                result.setdefault((r, col), []).append(appt)
        return result

    def _fetch_blocks(self) -> list:
        blocks: list = []
        for method_name in ("time_off_for_week", "breaks_for_week"):
            method = getattr(self.store, method_name, None)
            if callable(method):
                blocks.extend(method(self.week_start))
        return blocks

    def _block_cell_span(self, block: Any) -> tuple[tuple[int, int], int] | None:
        local_start = block.start.astimezone(SARAJEVO)
        local_end = block.end.astimezone(SARAJEVO)
        col = (local_start.date() - self.week_start).days
        if col < 0 or col >= self.DAY_COUNT:
            return None
        start_minutes = local_start.hour * 60 + local_start.minute
        end_minutes = local_end.hour * 60 + local_end.minute
        first = self.DAY_START_HOUR * 60
        last = self.DAY_END_HOUR * 60
        start_minutes = max(start_minutes, first)
        end_minutes = min(end_minutes, last)
        if end_minutes <= start_minutes:
            return None
        row = max(0, (start_minutes - first) // self.SLOT_MINUTES)
        span = max(1, math.ceil((end_minutes - start_minutes) / self.SLOT_MINUTES))
        return (row, col), min(span, self.rowCount() - row)

    # ---- prikaz ----

    def refresh(self) -> None:
        self.clearSpans()
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                old_widget = self.cellWidget(row, col)
                self.removeCellWidget(row, col)
                if old_widget is not None:
                    old_widget.deleteLater()
                item = QTableWidgetItem("")
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsDropEnabled
                )
                self.setItem(row, col, item)

        for block in self._fetch_blocks():
            if self._filter_doctor_id is not None and block.doctor_id != self._filter_doctor_id:
                continue
            span_info = self._block_cell_span(block)
            if span_info is None:
                continue
            (row, col), span = span_info
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
        for (row, col), span, appt in self._visible_appointments():
            cur_span, appts = grouped.get((row, col), (0, []))
            grouped[(row, col)] = (max(cur_span, span), appts + [appt])

        for (row, col), (span, appts) in grouped.items():
            if span > 1:
                self.setSpan(row, col, span, 1)
            cell_item = self.item(row, col)
            assert cell_item is not None
            lines: list[str] = []
            for appt in appts:
                doctor = getattr(appt, "doctor_name", None)
                suffix = f" [{doctor}]" if doctor and self._filter_doctor_id is None else ""
                lines.append(
                    f"{status_icon(appt)} {appt.patient_name} — {appt.service}{suffix}"
                )
            cell_item.setText("\n".join(lines))
            cell_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )
            cell_item.setData(_APPT_ID_ROLE, appts[0].id)
            if len(appts) == 1:
                cell_item.setForeground(QColor(0, 0, 0, 0))
                doctor_id = getattr(appts[0], "doctor_id", None)
                doctor_ids = list(self._doctor_colors)
                color_index = doctor_ids.index(doctor_id) if doctor_id in doctor_ids else 0
                background, border, text_color = self._DOCTOR_CARD_PALETTE[
                    color_index % len(self._DOCTOR_CARD_PALETTE)
                ]
                appt = appts[0]
                local_start = appt.start.astimezone(SARAJEVO)
                local_end = appt.end.astimezone(SARAJEVO)
                symbol, status_color = _status_visual(appt)
                doctor = getattr(appt, "doctor_name", None) or "Doktor"
                duration_minutes = (appt.end - appt.start).total_seconds() / 60
                compact = duration_minutes <= self.SLOT_MINUTES
                if compact:
                    card_text = (
                        f"<b>{appt.patient_name}</b><br>"
                        f"<span style='font-size:9px'>{local_start:%H:%M} – "
                        f"{local_end:%H:%M}&nbsp; "
                        f"<span style='color:{status_color}; font-size:13px; "
                        f"font-weight:700'>{symbol}</span>"
                        f"&nbsp; Dr {doctor}</span>"
                    )
                    card_style = (
                        f"background:{background}; color:{text_color}; "
                        f"border:1px solid {border}; "
                        f"border-left:4px solid {status_color}; border-radius:5px; "
                        "margin:1px 3px; padding:0 5px 0 6px; font-size:10px;"
                    )
                else:
                    card_text = (
                        f"<b>{appt.patient_name}</b><br>"
                        f"{local_start:%H:%M} – {local_end:%H:%M}<br>"
                        f"<span style='color:{status_color}; font-size:14px; "
                        f"font-weight:700'>{symbol}</span>"
                        f"&nbsp; Dr {doctor}"
                    )
                    card_style = (
                        f"background:{background}; color:{text_color}; "
                        f"border:1px solid {border}; "
                        f"border-left:4px solid {status_color}; border-radius:7px; "
                        "margin:4px 7px; padding:4px 7px 4px 8px; font-size:11px;"
                    )
                card = QLabel(card_text)
                card.setTextFormat(Qt.TextFormat.RichText)
                card.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                card.setWordWrap(False)
                card.setProperty("compact", compact)
                card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                card.setStyleSheet(card_style)
                self.setCellWidget(row, col, card)

    # ---- interakcije ----

    def _on_cell_clicked(self, row: int, col: int) -> None:
        appts = self._appointments_by_cell().get((row, col), [])
        if appts:
            self.appointment_clicked.emit(appts[0].id)
            return
        item = self.item(row, col)
        if item is not None and not item.data(_BLOCK_ROLE):
            self.slot_selected.emit(self._slot_datetime(row, col, self._pending_click_minutes))

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

        menu.exec(self.viewport().mapToGlobal(position))

    def move_appointment_to_slot(self, appt_id: int, row: int, col: int) -> bool:
        appt = self.store.get(appt_id)
        if appt is None:
            return False
        occupied = self._appointments_by_cell().get((row, col), [])
        if any(a.id != appt_id for a in occupied):
            return False
        new_start = self._slot_datetime(row, col)
        new_end = new_start + (appt.end - appt.start)
        try:
            self.store.move(appt_id, new_start, new_end)
        except OverlapError:
            return False
        self.refresh()
        self.appointment_moved.emit(appt)
        return True

    # ---- drag & drop ----

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            y = event.position().toPoint().y()
            row = self.rowAt(y)
            col = self.columnAt(event.position().toPoint().x())
            appts = self._appointments_by_cell().get((row, col), [])
            self._drag_appt_id = appts[0].id if appts else None
            self._pending_click_minutes = self._half_slot_minutes_at(y, row) if row >= 0 else 0
        super().mousePressEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        row = self.rowAt(event.position().toPoint().y())
        col = self.columnAt(event.position().toPoint().x())
        if self._drag_appt_id is None or row < 0 or col < 0:
            event.ignore()
            return
        if self.move_appointment_to_slot(self._drag_appt_id, row, col):
            event.accept()
        else:
            event.ignore()
