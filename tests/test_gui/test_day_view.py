"""Testovi dnevnog prikaza (DayView, Faza E)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from desktop.views.day_view import DayView

SARAJEVO = ZoneInfo("Europe/Sarajevo")
DAY = date(2026, 8, 17)  # ponedjeljak


def _render_day(view: DayView, service, day: date) -> None:
    """Fetch appointments + blocks i render-uj — helper (view ne fetch-uje sam)."""
    day_start = datetime(day.year, day.month, day.day, tzinfo=SARAJEVO)
    day_end = day_start + timedelta(days=1)
    appointments = service.appointments_for_range(day_start, day_end)
    week_start = day - timedelta(days=day.weekday())
    blocks = service.time_off_for_week(week_start) + service.breaks_for_week(week_start)
    view.render_schedule(appointments, blocks)


def test_day_view_ima_doktore_kao_kolone(qtbot, appointment_service) -> None:
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
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
    _render_day(view, appointment_service, DAY)
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
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    clicked: list[int] = []
    view.appointment_clicked.connect(clicked.append)
    view.cellClicked.emit(1, 0)  # Ljubo, 09:00
    assert clicked == [dto.id]


def test_klik_na_prazan_slot_emituje_slot_selected(qtbot, appointment_service) -> None:
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
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
    _render_day(view, appointment_service, DAY)
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
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    emitted: list[tuple[int, str]] = []
    view.appointment_action_requested.connect(lambda a, action: emitted.append((a, action)))

    menu = QMenu()
    view._add_menu_action(menu, "Izbriši termin", dto.id, "delete")
    action = next(a for a in menu.actions() if a.text() == "Izbriši termin")
    action.trigger()

    assert emitted == [(dto.id, "delete")]


def test_day_view_prikazuje_blockout(qtbot, appointment_service) -> None:
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    zorka_id = doctor_ids["Zorka"]
    appointment_service.create_time_off(
        zorka_id,
        datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 12, 0, tzinfo=SARAJEVO),
        reason="Godišnji",
    )
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    zorka_col = view._doctor_ids.index(zorka_id)
    item = view.item(2, zorka_col)  # 10:00 = red 2
    assert item is not None and item.text() == "Godišnji"


def test_klik_na_blockout_slot_ne_emituje_slot_selected(
    qtbot, appointment_service
) -> None:
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    zorka_id = doctor_ids["Zorka"]
    appointment_service.create_time_off(
        zorka_id,
        datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 12, 0, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    emitted: list[datetime] = []
    view.slot_selected.connect(emitted.append)
    zorka_col = view._doctor_ids.index(zorka_id)
    view.cellClicked.emit(2, zorka_col)  # 10:00, blokirano
    assert emitted == []


def test_visible_doctor_counts_za_dan(qtbot, appointment_service) -> None:
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    appointment_service.set_doctor(doctor_ids["Ljubo"])
    appointment_service.create(
        "A", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    appointment_service.set_doctor(doctor_ids["Ana"])
    appointment_service.create(
        "B", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 11, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 11, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    assert view.visible_doctor_counts() == {
        doctor_ids["Ljubo"]: 1,
        doctor_ids["Ana"]: 1,
    }


def test_prevlacenje_unutar_iste_doktor_kolone_azurira_vrijeme(
    qtbot, appointment_service
) -> None:
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    ljubo = doctor_ids["Ljubo"]
    appointment_service.set_doctor(ljubo)
    appt = appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    ljubo_col = view._doctor_ids.index(ljubo)
    assert view.move_appointment_to_slot(appt.id, 3, ljubo_col) is True  # 11:00
    assert appointment_service.get(appt.id).start == datetime(
        2026, 8, 17, 11, 0, tzinfo=SARAJEVO
    )


def test_move_ide_kroz_appointment_controller(
    qtbot, appointment_service, monkeypatch
) -> None:
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    ljubo = doctor_ids["Ljubo"]
    appointment_service.set_doctor(ljubo)
    appt = appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    ljubo_col = view._doctor_ids.index(ljubo)
    calls: list[tuple[int, datetime, datetime]] = []

    def _spy_move(appt_id: int, new_start: datetime, new_end: datetime) -> bool:
        calls.append((appt_id, new_start, new_end))
        return True

    monkeypatch.setattr(
        view._appointment_controller, "move_appointment_slot", _spy_move
    )

    assert view.move_appointment_to_slot(appt.id, 3, ljubo_col) is True  # 11:00
    assert calls == [
        (
            appt.id,
            datetime(2026, 8, 17, 11, 0, tzinfo=SARAJEVO),
            datetime(2026, 8, 17, 11, 30, tzinfo=SARAJEVO),
        )
    ]
    # Spy vraća True bez poziva store.move — start mora ostati 09:00.
    assert appointment_service.get(appt.id).start == datetime(
        2026, 8, 17, 9, 0, tzinfo=SARAJEVO
    )


def test_prevlacenje_u_zauzetu_celiju_se_odbija(
    qtbot, appointment_service
) -> None:
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    ljubo = doctor_ids["Ljubo"]
    appointment_service.set_doctor(ljubo)
    first = appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    appointment_service.create(
        "Marko", "062", "m@x", "Kontrola", "",
        datetime(2026, 8, 17, 11, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 11, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    ljubo_col = view._doctor_ids.index(ljubo)
    assert view.move_appointment_to_slot(first.id, 3, ljubo_col) is False  # 11:00 zauzeto
    assert appointment_service.get(first.id).start == datetime(
        2026, 8, 17, 9, 0, tzinfo=SARAJEVO
    )


def test_prevlacenje_u_drugu_doktor_kolonu_se_odbija(
    qtbot, appointment_service
) -> None:
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    ljubo = doctor_ids["Ljubo"]
    zorka = doctor_ids["Zorka"]
    appointment_service.set_doctor(ljubo)
    appt = appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    zorka_col = view._doctor_ids.index(zorka)
    assert view.move_appointment_to_slot(appt.id, 1, zorka_col) is False
    moved = appointment_service.get(appt.id)
    assert moved.doctor_id == ljubo
    assert moved.start == datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO)


def test_preklapanje_sa_terminom_van_prikaza_se_odbija(
    qtbot, appointment_service
) -> None:
    """OverlapError iz store.move() — termin prije radnog vremena DayView-a
    nije u _appointments_by_cell, ali se vremenski preklapa sa ciljnim slotom."""
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    ljubo = doctor_ids["Ljubo"]
    appointment_service.set_doctor(ljubo)
    appt = appointment_service.create(
        "Ana", "061", "a@x", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    appointment_service.create(
        "Marko", "062", "m@x", "Kontrola", "",
        datetime(2026, 8, 17, 7, 30, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 8, 30, tzinfo=SARAJEVO),
    )
    view = DayView(appointment_service, DAY)
    _render_day(view, appointment_service, DAY)
    qtbot.addWidget(view)

    ljubo_col = view._doctor_ids.index(ljubo)
    assert view.move_appointment_to_slot(appt.id, 0, ljubo_col) is False  # 08:00
    assert appointment_service.get(appt.id).start == datetime(
        2026, 8, 17, 9, 0, tzinfo=SARAJEVO
    )
