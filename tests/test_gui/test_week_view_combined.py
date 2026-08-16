"""Testovi kombinovanog sedmičnog prikaza (više doktora, boje, filter)."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from PySide6.QtGui import QColor

from desktop.fake_data import SARAJEVO
from desktop.views.week_view import WeekView

WEEK_START = date(2026, 8, 17)


def _at(day_offset: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 17 + day_offset, hour, minute, tzinfo=SARAJEVO)


@pytest.fixture()
def doctor_ids(appointment_service) -> dict[str, int]:
    return {d.ime: d.id for d in appointment_service.doctors()}


@pytest.fixture()
def week_view(qtbot, appointment_service, doctor_ids) -> WeekView:
    appointment_service.set_doctor(doctor_ids["Ljubo"])
    appointment_service.create(
        "Ana Anić", "061", "a@x", "Kontrola", "", _at(0, 9), _at(0, 9, 30)
    )
    appointment_service.set_doctor(doctor_ids["Zorka"])
    appointment_service.create(
        "Marko Marković", "062", "m@x", "Kontrola", "", _at(1, 10), _at(1, 10, 30)
    )
    view = WeekView(appointment_service, WEEK_START)
    qtbot.addWidget(view)
    return view


def _all_item_texts(view: WeekView) -> str:
    texts = []
    for row in range(view.rowCount()):
        for col in range(view.columnCount()):
            item = view.item(row, col)
            if item is not None and item.text():
                texts.append(item.text())
    return "\n".join(texts)


def test_kombinovani_prikaz_prikazuje_oba_doktora(week_view: WeekView) -> None:
    joined = _all_item_texts(week_view)
    assert "Ana Anić" in joined
    assert "Marko Marković" in joined
    assert "[Ljubo]" in joined
    assert "[Zorka]" in joined


def test_boje_po_doktoru_se_razlikuju(week_view: WeekView, doctor_ids: dict[str, int]) -> None:
    ljubo_item = week_view.item(2, 0)  # pon 09:00 → Ljubo
    zorka_item = week_view.item(4, 1)  # uto 10:00 → Zorka
    assert ljubo_item is not None and zorka_item is not None
    ljubo_color = ljubo_item.background().color()
    zorka_color = zorka_item.background().color()
    assert ljubo_color != zorka_color
    assert ljubo_color != QColor(255, 255, 255)
    assert zorka_color != QColor(255, 255, 255)


def test_filter_prikazuje_samo_jednog_doktora(
    week_view: WeekView, doctor_ids: dict[str, int]
) -> None:
    week_view.set_filter(doctor_ids["Ljubo"])
    joined = _all_item_texts(week_view)
    assert "Ana Anić" in joined
    assert "Marko Marković" not in joined
    assert "[Ljubo]" not in joined  # u filteru jednog doktora nema sufiksa


def test_filter_none_vraca_sve(week_view: WeekView) -> None:
    week_view.set_filter(None)
    joined = _all_item_texts(week_view)
    assert "Ana Anić" in joined
    assert "Marko Marković" in joined
