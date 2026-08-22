"""Testovi panela za blokiranje vremena (DENT-IMPROVE-004)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import QDialog, QLabel, QPushButton

from desktop.fake_data import SARAJEVO
from desktop.views import blockout_panel as blockout_panel_mod
from desktop.views.blockout_panel import BlockoutPanel
from desktop.views.dialogs.blockout_delete_confirm import BlockoutDeleteConfirmDialog


class BlockoutStore:
    def __init__(self) -> None:
        self.created: list[tuple] = []
        self.deleted: list[int] = []
        self._blocks = [
            SimpleNamespace(
                id=1,
                doctor_id=1,
                doctor_name="Ljubo",
                start=datetime(2026, 8, 18, 12, 0, tzinfo=SARAJEVO),
                end=datetime(2026, 8, 18, 13, 0, tzinfo=SARAJEVO),
                reason="Ručak",
            )
        ]

    def doctors(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, ime="Ljubo"), SimpleNamespace(id=2, ime="Zorka")]

    def list_time_off(self) -> list[SimpleNamespace]:
        return list(self._blocks)

    def create_time_off(self, doctor_id: int, start, end, reason=None) -> None:
        self.created.append((doctor_id, start, end, reason))
        self._blocks.append(
            SimpleNamespace(
                id=99,
                doctor_id=doctor_id,
                doctor_name="Ljubo" if doctor_id == 1 else "Zorka",
                start=start,
                end=end,
                reason=reason or "",
            )
        )

    def delete_time_off(self, block_id: int) -> None:
        self.deleted.append(block_id)
        self._blocks = [b for b in self._blocks if b.id != block_id]


def _button(widget, text: str) -> QPushButton:
    for button in widget.findChildren(QPushButton):
        if button.text() == text:
            return button
    raise AssertionError(f"dugme '{text}' nije pronađeno")


def _labels(widget) -> str:
    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_panel_prikazuje_aktivne_blokade(qtbot) -> None:
    panel = BlockoutPanel(BlockoutStore())
    qtbot.addWidget(panel)

    assert panel.list_box.title() == "Aktivne blokade (1)"
    assert "Ljubo" in _labels(panel.list_box)
    assert "Ručak" in _labels(panel.list_box)
    assert panel.doctor_combo.count() == 2


def test_save_validan_poziva_create_time_off(qtbot) -> None:
    store = BlockoutStore()
    panel = BlockoutPanel(store)
    qtbot.addWidget(panel)

    panel.date_edit.setDate(QDate(2026, 8, 18))
    panel.start_edit.setTime(QTime(9, 0))
    panel.end_edit.setTime(QTime(10, 0))
    panel.reason_edit.setText("Ručak")

    qtbot.mouseClick(_button(panel, "Sačuvaj"), Qt.MouseButton.LeftButton)

    expected_start = datetime(2026, 8, 18, 9, 0, tzinfo=SARAJEVO)
    expected_end = datetime(2026, 8, 18, 10, 0, tzinfo=SARAJEVO)
    assert store.created == [(1, expected_start, expected_end, "Ručak")]


def test_save_end_pre_start_prikazuje_gresku(qtbot) -> None:
    store = BlockoutStore()
    panel = BlockoutPanel(store)
    qtbot.addWidget(panel)

    panel.start_edit.setTime(QTime(10, 0))
    panel.end_edit.setTime(QTime(9, 0))

    qtbot.mouseClick(_button(panel, "Sačuvaj"), Qt.MouseButton.LeftButton)

    assert store.created == []
    assert not panel.error_label.isHidden()
    assert "poslije početka" in panel.error_label.text()


def test_delete_uz_potvrdu_poziva_delete_time_off(qtbot, monkeypatch) -> None:
    store = BlockoutStore()
    panel = BlockoutPanel(store)
    qtbot.addWidget(panel)

    class FakeDeleteDialog:
        def __init__(self, block, parent=None):
            self.block = block

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(blockout_panel_mod, "BlockoutDeleteConfirmDialog", FakeDeleteDialog)

    qtbot.mouseClick(_button(panel, "Obriši"), Qt.MouseButton.LeftButton)
    qtbot.wait(10)  # dovrši deleteLater() stare stavke

    assert store.deleted == [1]
    assert panel.list_box.title() == "Aktivne blokade (0)"


def test_delete_odustani_ne_brise_blokadu(qtbot, monkeypatch) -> None:
    store = BlockoutStore()
    panel = BlockoutPanel(store)
    qtbot.addWidget(panel)

    class FakeDeleteDialog:
        def __init__(self, block, parent=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(blockout_panel_mod, "BlockoutDeleteConfirmDialog", FakeDeleteDialog)

    qtbot.mouseClick(_button(panel, "Obriši"), Qt.MouseButton.LeftButton)
    qtbot.wait(10)  # dovrši deleteLater() stare stavke

    assert store.deleted == []
    assert panel.list_box.title() == "Aktivne blokade (1)"


def test_blockout_delete_dialog_prikazuje_doktora_vrijeme_i_razlog(qtbot) -> None:
    block = SimpleNamespace(
        id=1,
        doctor_name="Ljubo",
        start=datetime(2026, 8, 18, 12, 0, tzinfo=SARAJEVO),
        end=datetime(2026, 8, 18, 13, 0, tzinfo=SARAJEVO),
        reason="Ručak",
    )
    dialog = BlockoutDeleteConfirmDialog(block)
    qtbot.addWidget(dialog)

    patient = dialog.findChild(QLabel, "deletePatient")
    when = dialog.findChild(QLabel, "deleteWhen")
    reason = dialog.findChild(QLabel, "deleteNote")
    assert patient is not None and patient.text() == "Ljubo"
    assert when is not None and "12:00" in when.text() and "13:00" in when.text()
    assert reason is not None and "Ručak" in reason.text()
