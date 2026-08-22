"""Panel za kreiranje i uklanjanje blokiranog vremena (odsustva) doktora."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from PySide6.QtCore import QDate, Qt, QTime, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from dentaland.services import OverlapError
from desktop.fake_data import SARAJEVO
from desktop.views.dialogs.blockout_delete_confirm import BlockoutDeleteConfirmDialog


class BlockoutPanel(QScrollArea):
    """Forma + lista aktivnih blokada; svaka izmjena emituje ``changed``."""

    changed = Signal()

    def __init__(self, store: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.setObjectName("blockoutPanel")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(26, 18, 14, 14)
        layout.setSpacing(14)

        title = QLabel("Blokiraj vrijeme")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Odsustvo ili pauza doktora — blokada se prikazuje na kalendaru.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form_box = QGroupBox("Nova blokada")
        form_box.setObjectName("dashboardBox")
        form = QFormLayout(form_box)
        form.setSpacing(10)

        self.doctor_combo = QComboBox()
        form.addRow("Doktor", self.doctor_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Datum", self.date_edit)

        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.start_edit.setTime(QTime(8, 0))
        form.addRow("Od", self.start_edit)

        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        self.end_edit.setTime(QTime(9, 0))
        form.addRow("Do", self.end_edit)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("razlog (opciono)")
        form.addRow("Razlog", self.reason_edit)

        self.error_label = QLabel()
        self.error_label.setObjectName("dialogError")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)

        save_button = QPushButton("Sačuvaj")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._on_save)

        layout.addWidget(form_box)
        layout.addWidget(self.error_label)
        layout.addWidget(save_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.list_box = QGroupBox("Aktivne blokade")
        self.list_box.setObjectName("dashboardBox")
        layout.addWidget(self.list_box, 1)

        self.setWidget(container)
        self.refresh()

    # ---- refresh ----

    def refresh(self) -> None:
        self._refresh_doctors()
        self._refresh_list()

    def _refresh_doctors(self) -> None:
        self.doctor_combo.clear()
        doctors_fn = getattr(self.store, "doctors", None)
        for doctor in doctors_fn() if callable(doctors_fn) else []:
            self.doctor_combo.addItem(doctor.ime, doctor.id)

    def _refresh_list(self) -> None:
        old = self.list_box.layout()
        if old is None:
            old = QVBoxLayout(self.list_box)
        while old.count():
            item = old.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        blocks_fn = getattr(self.store, "list_time_off", None)
        blocks = list(blocks_fn()) if callable(blocks_fn) else []
        self.list_box.setTitle(f"Aktivne blokade ({len(blocks)})")
        if not blocks:
            old.addWidget(QLabel("Nema aktivnih blokada."))
            return
        for block in blocks:
            start = block.start.astimezone(SARAJEVO)
            end = block.end.astimezone(SARAJEVO)
            reason = f" · {block.reason}" if block.reason else ""
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 3, 0, 3)
            row_layout.setSpacing(5)
            details = QLabel(
                f"<b>{block.doctor_name}</b><br>"
                f"<span style='color:#31578a'>{start:%d.%m.%Y. %H:%M} – "
                f"{end:%H:%M}{reason}</span>"
            )
            row_layout.addWidget(details, 1)
            delete = QPushButton("Obriši")
            delete.setObjectName("rejectButton")
            delete.clicked.connect(
                lambda _checked=False, block=block: self._on_delete(block)
            )
            row_layout.addWidget(delete)
            old.addWidget(row)

    # ---- akcije ----

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _clear_error(self) -> None:
        self.error_label.setText("")
        self.error_label.setVisible(False)

    def _on_save(self) -> None:
        self._clear_error()
        doctor_id = self.doctor_combo.currentData()
        if doctor_id is None:
            self._show_error("Izaberite doktora.")
            return
        qdate = self.date_edit.date()
        day = date(qdate.year(), qdate.month(), qdate.day())
        qstart = self.start_edit.time()
        start_time = time(qstart.hour(), qstart.minute())
        qend = self.end_edit.time()
        end_time = time(qend.hour(), qend.minute())
        if end_time <= start_time:
            self._show_error("Kraj blokade mora biti poslije početka.")
            return
        start = datetime.combine(day, start_time, tzinfo=SARAJEVO)
        end = datetime.combine(day, end_time, tzinfo=SARAJEVO)
        reason = self.reason_edit.text().strip() or None
        try:
            self.store.create_time_off(doctor_id, start, end, reason)
        except (OverlapError, ValueError) as exc:
            self._show_error(str(exc))
            return
        self.reason_edit.clear()
        self.refresh()
        self.changed.emit()

    def _on_delete(self, block: Any) -> None:
        dialog = BlockoutDeleteConfirmDialog(block, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._clear_error()
        try:
            self.store.delete_time_off(block.id)
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.refresh()
        self.changed.emit()
