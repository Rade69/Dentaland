"""Testovi dnevnog prikaza (DayView, Faza E)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from desktop.views.day_view import DayView

SARAJEVO = ZoneInfo("Europe/Sarajevo")
DAY = date(2026, 8, 17)  # ponedjeljak


def test_day_view_ima_doktore_kao_kolone(qtbot, appointment_service) -> None:
    view = DayView(appointment_service, DAY)
    qtbot.addWidget(view)

    assert view.columnCount() == 3  # Ljubo, Zorka, Ana
    assert view.horizontalHeaderItem(0).text() == "Ljubo"
    assert view.horizontalHeaderItem(1).text() == "Zorka"
    assert view.horizontalHeaderItem(2).text() == "Ana"


def test_day_view_prikazuje_termin_u_koloni_doktora(
    qtbot, appointment_service
) -> None:
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    appointment_service.set_doctor(doctor_ids["Zorka"])
    appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    qtbot.addWidget(view)

    zorka_col = view._doctor_ids.index(doctor_ids["Zorka"])
    item = view.item(1, zorka_col)  # 09:00 = red 1
    assert item is not None and "Ana" in item.text()
    assert view.item(1, 0).text() == ""  # Ljubo kolona prazna


def test_klik_na_termin_emituje_appointment_clicked(qtbot, appointment_service) -> None:
    dto = appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    qtbot.addWidget(view)

    clicked: list[int] = []
    view.appointment_clicked.connect(clicked.append)
    view.cellClicked.emit(1, 0)  # Ljubo, 09:00
    assert clicked == [dto.id]


def test_klik_na_prazan_slot_emituje_slot_selected(qtbot, appointment_service) -> None:
    view = DayView(appointment_service, DAY)
    qtbot.addWidget(view)

    emitted: list[datetime] = []
    view.slot_selected.connect(emitted.append)
    view.cellClicked.emit(0, 0)  # 08:00 prazno
    assert emitted == [datetime(2026, 8, 17, 8, 0, tzinfo=SARAJEVO)]


def test_visible_status_counts_za_dan(qtbot, appointment_service) -> None:
    appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    qtbot.addWidget(view)

    counts = view.visible_status_counts()
    assert counts["waiting"] == 1


def test_izbrisi_termin_emituje_delete_akciju(qtbot, appointment_service) -> None:
    """Faza F (HIGH) — Izbriši termin dostupno i u Dan prikazu."""
    from PySide6.QtWidgets import QMenu

    dto = appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    qtbot.addWidget(view)

    emitted: list[tuple[int, str]] = []
    view.appointment_action_requested.connect(lambda a, action: emitted.append((a, action)))

    menu = QMenu()
    view._add_menu_action(menu, "Izbriši termin", dto.id, "delete")
    action = next(a for a in menu.actions() if a.text() == "Izbriši termin")
    action.trigger()

    assert emitted == [(dto.id, "delete")]
