"""Testovi tri semantički različita desna dashboard panela."""

from datetime import date, datetime
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from desktop.fake_data import SARAJEVO
from desktop.views.requests_panel import DashboardPanels


class DashboardStore:
    def __init__(self) -> None:
        self.confirmed_ids: list[int] = []
        self._awaiting = [
            SimpleNamespace(
                id=7,
                patient_name="Marko Bošnjak",
                service="Kontrola",
                start=datetime(2026, 8, 18, 11, 30, tzinfo=SARAJEVO),
            )
        ]

    def pending_requests(self):
        return [SimpleNamespace(id=1, ime="Jelena Kovač", requested_date=date(2026, 8, 18))]

    def awaiting_confirmation(self):
        return list(self._awaiting)

    def cancelled_today(self):
        return [
            SimpleNamespace(
                patient_name="Ivana M.",
                service="Pregled",
                start=datetime(2026, 8, 17, 14, 0, tzinfo=SARAJEVO),
            )
        ]

    def mark_confirmed(self, appt_id: int) -> None:
        self.confirmed_ids.append(appt_id)
        self._awaiting = [a for a in self._awaiting if a.id != appt_id]


def _labels(box) -> str:
    return "\n".join(label.text() for label in box.findChildren(QLabel))


def test_paneli_ne_mijesaju_zahtjeve_i_termine(qtbot) -> None:
    panels = DashboardPanels(DashboardStore())
    qtbot.addWidget(panels)

    assert panels.pending_box.title() == "Novi zahtjevi (1)"
    assert "Jelena Kovač" in _labels(panels.pending_box)
    assert "Kontrola" not in _labels(panels.pending_box)

    assert panels.awaiting_box.title() == "Čekaju potvrdu (1)"
    assert "Marko Bošnjak" in _labels(panels.awaiting_box)
    assert "Kontrola" in _labels(panels.awaiting_box)

    assert panels.cancelled_box.title() == "Otkazani danas (1)"
    assert "Ivana M." in _labels(panels.cancelled_box)
    assert "Pregled" in _labels(panels.cancelled_box)


def test_cekaju_potvrdu_ima_dugme_potvrdi_a_otkazani_nemaju(qtbot) -> None:
    panels = DashboardPanels(DashboardStore())
    qtbot.addWidget(panels)

    assert panels.awaiting_box.findChildren(QPushButton)
    assert not panels.cancelled_box.findChildren(QPushButton)


def test_klik_na_potvrdi_zove_mark_confirmed_i_uklanja_stavku(qtbot) -> None:
    store = DashboardStore()
    panels = DashboardPanels(store)
    qtbot.addWidget(panels)

    button = panels.awaiting_box.findChildren(QPushButton)[0]
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    qtbot.wait(10)  # dovrši deleteLater() od stare stavke (deferred delete event)

    assert store.confirmed_ids == [7]
    assert panels.awaiting_box.title() == "Čekaju potvrdu (0)"
    assert "Marko Bošnjak" not in _labels(panels.awaiting_box)
