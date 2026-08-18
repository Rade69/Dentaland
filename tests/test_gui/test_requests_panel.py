"""Testovi tri semantički različita desna dashboard panela."""

from datetime import date, datetime
from types import SimpleNamespace

from PySide6.QtWidgets import QLabel

from desktop.fake_data import SARAJEVO
from desktop.views.requests_panel import DashboardPanels


class DashboardStore:
    def pending_requests(self):
        return [SimpleNamespace(id=1, ime="Jelena Kovač", requested_date=date(2026, 8, 18))]

    def awaiting_confirmation(self):
        return [
            SimpleNamespace(
                patient_name="Marko Bošnjak",
                service="Kontrola",
                start=datetime(2026, 8, 18, 11, 30, tzinfo=SARAJEVO),
            )
        ]

    def cancelled_today(self):
        return [
            SimpleNamespace(
                patient_name="Ivana M.",
                service="Pregled",
                start=datetime(2026, 8, 17, 14, 0, tzinfo=SARAJEVO),
            )
        ]


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
