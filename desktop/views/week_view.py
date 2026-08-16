"""Sedmični prikaz kalendara — početni ekran desktop aplikacije.

Prikazuje 7 dana (ponedjeljak–nedjelja) kao mrežu vremenskih slotova.
Klik na prazan slot emituje ``slot_selected`` (otvara dijalog za unos);
prevlačenje zauzetog slota na prazan mijenja vrijeme termina u store-u.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, Signal
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

    def __init__(self, store, week_start: date, parent=None):
        super().__init__(parent)
        self.store = store
        self.week_start = week_start
        self._drag_appt_id: int | None = None

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

    def _appointments_by_cell(self) -> dict[tuple[int, int], AppointmentDTO]:
        result: dict[tuple[int, int], AppointmentDTO] = {}
        for appt in self.store.all():
            cell = self._cell_for(appt)
            if cell is not None:
                result[cell] = appt
        return result

    # ---- prikaz ----

    def refresh(self) -> None:
        by_cell = self._appointments_by_cell()
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = QTableWidgetItem("")
                appt = by_cell.get((row, col))
                if appt is not None:
                    item.setText(f"{appt.patient_name} — {appt.service}")
                    item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsDragEnabled
                    )
                    item.setData(_APPT_ID_ROLE, appt.id)
                else:
                    item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsDropEnabled
                    )
                self.setItem(row, col, item)

    # ---- interakcije ----

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if self._appointments_by_cell().get((row, col)) is None:
            self.slot_selected.emit(self._slot_datetime(row, col))

    def move_appointment_to_slot(self, appt_id: int, row: int, col: int) -> bool:
        appt = self.store.get(appt_id)
        if appt is None or self._appointments_by_cell().get((row, col)) is not None:
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
