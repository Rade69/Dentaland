"""Testovi dedicated stranice za nove zahtjeve (DENT-IMPROVE-006)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton

from desktop.views import requests_page as requests_page_mod
from desktop.views.requests_page import RequestsPage


class RequestsStore:
    def __init__(self) -> None:
        self.requests = [
            SimpleNamespace(
                id=1,
                ime="Jelena Kovač",
                telefon="061/111-222",
                email="jelena@example.com",
                requested_date=date(2026, 8, 22),
                created_at=datetime(2026, 8, 21, 7, 15, tzinfo=UTC),
            )
        ]

    def pending_requests(self):
        return list(self.requests)


def _labels(page: RequestsPage) -> str:
    return "\n".join(label.text() for label in page.findChildren(QLabel))


def _process_button(page: RequestsPage) -> QPushButton:
    return next(button for button in page.findChildren(QPushButton) if button.text() == "Obradi")


def test_stranica_prikazuje_pending_count_i_sve_trazene_podatke(qtbot) -> None:
    page = RequestsPage(RequestsStore())
    qtbot.addWidget(page)

    labels = _labels(page)
    assert "1 neobrađen zahtjev" in labels
    assert "Jelena Kovač" in labels
    assert "061/111-222" in labels
    assert "jelena@example.com" in labels
    assert "Traženi datum: 22.08.2026." in labels
    assert "Poslano: 21.08.2026. u 09:15" in labels
    assert "JK" in labels
    assert "NOVO" in labels
    assert "Savjet" in labels


def test_stranica_koristi_nove_summary_kartice_i_status_elemente(qtbot) -> None:
    page = RequestsPage(RequestsStore())
    qtbot.addWidget(page)

    assert page.findChild(QFrame, "requestsSummary") is not None
    assert page.findChild(QFrame, "requestsTip") is not None
    row = page.findChild(QFrame, "requestPageRow")
    assert row is not None
    assert row.findChild(QLabel, "requestInitials").text() == "JK"
    assert row.findChild(QLabel, "requestNewBadge").text() == "NOVO"
    assert row.findChild(QLabel, "requestMore").text() == "⋮"
    assert _process_button(page).size().width() == 98


def test_vrijeme_slanja_koristi_danas_za_danasnji_zahtjev() -> None:
    sent = datetime(2026, 8, 22, 5, 51, tzinfo=UTC)
    assert requests_page_mod._sent_text(sent, date(2026, 8, 22)) == (
        "Poslano: danas u 07:51"
    )


def test_obrada_koristi_zajednicki_tok_i_osvjezava_listu(qtbot, monkeypatch) -> None:
    store = RequestsStore()
    processed = []

    def fake_process(actual_store, request, parent):
        processed.append((actual_store, request.id, parent))
        actual_store.requests.clear()
        return True

    monkeypatch.setattr(requests_page_mod, "process_pending_request", fake_process)
    page = RequestsPage(store)
    qtbot.addWidget(page)

    qtbot.mouseClick(_process_button(page), Qt.MouseButton.LeftButton)
    qtbot.wait(10)

    assert processed == [(store, 1, page)]
    assert "0 neobrađena zahtjeva" in _labels(page)
    assert "Sve je obrađeno." in _labels(page)
