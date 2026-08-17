"""Testovi sedmičnog prikaza (WeekView)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from desktop.fake_data import SARAJEVO, FakeStore
from desktop.views.week_view import WeekView


@pytest.fixture()
def week_view(qtbot, store: FakeStore, week_start: date) -> WeekView:
    view = WeekView(store, week_start)
    qtbot.addWidget(view)
    return view


def test_sedmieni_prikaz_ima_sedam_dana(week_view: WeekView) -> None:
    assert week_view.columnCount() == 7
    assert week_view.rowCount() == 20  # 08:00–18:00, korak 30 min


def test_klik_na_prazan_slot_emituje_vrijeme(week_view: WeekView) -> None:
    emitted: list[datetime] = []
    week_view.slot_selected.connect(emitted.append)
    week_view.cellClicked.emit(0, 0)  # ponedjeljak 08:00, prazno
    assert emitted == [datetime(2026, 8, 17, 8, 0, tzinfo=SARAJEVO)]


def test_prevlacenje_termina_azurira_vrijeme(store: FakeStore, week_view: WeekView) -> None:
    appt = store.create(
        "Ana Anić", "061/111-222", "ana@example.com", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    week_view.refresh()

    assert week_view.move_appointment_to_slot(appt.id, 4, 1) is True  # utorak 10:00
    assert store.get(appt.id).start == datetime(2026, 8, 18, 10, 0, tzinfo=SARAJEVO)

    new_item = week_view.item(4, 1)
    assert new_item is not None and "Ana Anić" in new_item.text()
    old_item = week_view.item(2, 0)
    assert old_item is not None and old_item.text() == ""


def test_zauzet_slot_prikazuje_ime_i_uslugu(store: FakeStore, week_view: WeekView) -> None:
    store.create(
        "Ana Anić", "061/111-222", "ana@example.com", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    week_view.refresh()

    item = week_view.item(2, 0)  # ponedjeljak 09:00
    assert item is not None
    assert "Ana Anić" in item.text()
    assert "Kontrola" in item.text()


def test_termin_od_60_min_je_spojen_preko_dva_slota(
    store: FakeStore, week_view: WeekView
) -> None:
    store.create(
        "Ana Anić", "061/111-222", "ana@example.com", "Plomba", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO),
    )
    week_view.refresh()

    assert week_view.rowSpan(2, 0) == 2  # ponedjeljak 09:00–10:00


def test_termin_od_90_min_je_spojen_preko_tri_slota(
    store: FakeStore, week_view: WeekView
) -> None:
    store.create(
        "Ana Anić", "061/111-222", "ana@example.com", "Izbjeljivanje", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 10, 30, tzinfo=SARAJEVO),
    )
    week_view.refresh()

    assert week_view.rowSpan(2, 0) == 3  # ponedjeljak 09:00–10:30


def test_klik_na_pokrivenu_celiju_ne_otvara_dijalog(
    store: FakeStore, week_view: WeekView
) -> None:
    store.create(
        "Ana Anić", "061/111-222", "ana@example.com", "Plomba", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO),
    )
    week_view.refresh()

    emitted: list[datetime] = []
    week_view.slot_selected.connect(emitted.append)
    week_view.cellClicked.emit(3, 0)  # ponedjeljak 09:30 — sredina termina
    assert emitted == []


def test_drag_drop_odbija_pokrivenu_celiju(store: FakeStore, week_view: WeekView) -> None:
    store.create(
        "Ana Anić", "061/111-222", "ana@example.com", "Plomba", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO),
    )
    other = store.create(
        "Marko Marković", "062/222-333", "marko@example.com", "Kontrola", "",
        datetime(2026, 8, 17, 11, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 11, 30, tzinfo=SARAJEVO),
    )
    week_view.refresh()

    assert week_view.move_appointment_to_slot(other.id, 3, 0) is False  # 09:30 — sredina


def test_termin_od_30_min_nije_spojen(store: FakeStore, week_view: WeekView) -> None:
    store.create(
        "Ana Anić", "061/111-222", "ana@example.com", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    week_view.refresh()

    assert week_view.rowSpan(2, 0) == 1
