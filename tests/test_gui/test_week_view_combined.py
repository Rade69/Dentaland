"""Testovi kombinovanog sedmičnog prikaza (više doktora, boje, filter)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

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
    ljubo_card = week_view.cellWidget(2, 0)  # pon 09:00 → Ljubo
    zorka_card = week_view.cellWidget(4, 1)  # uto 10:00 → Zorka
    assert ljubo_card is not None and zorka_card is not None
    assert "#ebf8ed" in ljubo_card.styleSheet()
    assert "#fff0f2" in zorka_card.styleSheet()


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


def test_termin_od_60_min_spojen_preko_dva_slota(
    week_view: WeekView, appointment_service, doctor_ids: dict[str, int]
) -> None:
    appointment_service.set_doctor(doctor_ids["Ljubo"])
    appointment_service.create(
        "Petar Petrović", "063", "p@x", "Plomba", "", _at(2, 9), _at(2, 10)
    )
    week_view.refresh()

    assert week_view.rowSpan(2, 2) == 2  # srijeda 09:00–10:00
