"""Sedmični prikaz kalendara — početni ekran desktop aplikacije.

Prikazuje 7 dana (ponedjeljak–nedjelja) kao mrežu vremenskih slotova.
Podržava termine više doktora istovremeno, boja-kodirano po doktoru, i
filtriranje po jednom doktoru (``set_filter``). Klik na prazan slot emituje
``slot_selected`` (otvara dijalog za unos); prevlačenje zauzetog slota mijenja
vrijeme termina — overlap provjerava servisni sloj (``OverlapError``).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QTableWidget,
    QTableWidgetItem,
)

from dentaland.services import AppointmentDTO, OverlapError
from desktop.fake_data import SARAJEVO

_APPT_ID_ROLE = Qt.ItemDataRole.UserRole


class WeekView(QTableWidget):
    """Mreža sedmičnog rasporeda (redovi = vrijeme, kolone = dani)."""

    slot_selected = Signal(object)  # datetime početka praznog slota
    appointment_moved = Signal(object)  # Appointment koji je pomjeren

    DAY_NAMES = [
        "Ponedjeljak", "Utorak", "Srijeda", "Četvrtak",
        "Petak", "Subota", "Nedjelja",
    ]
    DAY_COUNT = 7
    DAY_START_HOUR = 8
    DAY_END_HOUR = 18
    SLOT_MINUTES = 30

    _DOCTOR_PALETTE = ["#A5D6A7", "#EF9A9A", "#90CAF9", "#FFE082", "#CE93D8", "#80DEEA"]

    def __init__(self, store, week_start: date, parent=None):
        super().__init__(parent)
        self.store = store
        self.week_start = week_start
        self._drag_appt_id: int | None = None
        self._filter_doctor_id: int | None = None
        self._doctor_colors = self._build_doctor_colors()

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

        self.setDragDropMode(QTableWidget.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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

    # ---- mapiranje slot ↔ vrijeme ----

    @staticmethod
    def _format_minutes(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _slot_datetime(self, row: int, col: int) -> datetime:
        day = self.week_start + timedelta(days=col)
        minutes = self.DAY_START_HOUR * 60 + row * self.SLOT_MINUTES
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
        if offset < 0 or offset % self.SLOT_MINUTES != 0:
            return None
        row = offset // self.SLOT_MINUTES
        if row >= self.rowCount():
            return None
        return row, col

    def _fetch_appointments(self) -> list[AppointmentDTO]:
        fetch = getattr(self.store, "all_combined", None)
        if callable(fetch):
            return fetch()
        return self.store.all()

    def _appointments_by_cell(self) -> dict[tuple[int, int], list[AppointmentDTO]]:
        result: dict[tuple[int, int], list[AppointmentDTO]] = {}
        for appt in self._fetch_appointments():
            appt_doctor = getattr(appt, "doctor_id", None)
            if self._filter_doctor_id is not None and appt_doctor != self._filter_doctor_id:
                continue
            cell = self._cell_for(appt)
            if cell is not None:
                result.setdefault(cell, []).append(appt)
        return result

    # ---- prikaz ----

    def refresh(self) -> None:
        by_cell = self._appointments_by_cell()
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = QTableWidgetItem("")
                appts = by_cell.get((row, col), [])
                if appts:
                    lines: list[str] = []
                    for appt in appts:
                        doctor = getattr(appt, "doctor_name", None)
                        suffix = f" [{doctor}]" if doctor and self._filter_doctor_id is None else ""
                        lines.append(f"{appt.patient_name} — {appt.service}{suffix}")
                    item.setText("\n".join(lines))
                    item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsDragEnabled
                    )
                    item.setData(_APPT_ID_ROLE, appts[0].id)
                    if len(appts) == 1:
                        color = self._doctor_colors.get(getattr(appts[0], "doctor_id", None))
                        if color is not None:
                            item.setBackground(color)
                else:
                    item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsDropEnabled
                    )
                self.setItem(row, col, item)

    # ---- interakcije ----

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if not self._appointments_by_cell().get((row, col)):
            self.slot_selected.emit(self._slot_datetime(row, col))

    def move_appointment_to_slot(self, appt_id: int, row: int, col: int) -> bool:
        appt = self.store.get(appt_id)
        if appt is None:
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

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            self._drag_appt_id = item.data(_APPT_ID_ROLE) if item is not None else None
        super().mousePressEvent(event)

    def dropEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if self._drag_appt_id is None or not index.isValid():
            event.ignore()
            return
        if self.move_appointment_to_slot(self._drag_appt_id, index.row(), index.column()):
            event.accept()
        else:
            event.ignore()
