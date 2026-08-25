"""Testovi ScheduleController-a (REF-05).

Dokazuju da jedan ``refresh()`` radi tačno JEDAN ``appointments_for_range``
fetch (plus po jedan ``time_off_for_week``/``breaks_for_week``), da renderuje
SAMO aktivan view (skriveni se ne dira), i da status/doctor counts dolaze iz
ISTOG render-ovanog dataseta bez dodatnog fetch-a.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from desktop.controllers.schedule_controller import ScheduleController

WEEK_START = date(2026, 8, 17)


class _CountingStore:
    """Fake store koji broji fetch pozive, bez SQL-a."""

    def __init__(self) -> None:
        self.appointments_for_range_calls = 0
        self.time_off_for_week_calls = 0
        self.breaks_for_week_calls = 0

    def appointments_for_range(self, start: datetime, end: datetime) -> list:
        self.appointments_for_range_calls += 1
        appt_start = start + timedelta(hours=1)
        return [
            {
                "id": 1,
                "start": appt_start,
                "end": appt_start + timedelta(minutes=30),
                "doctor_id": 1,
                "doctor_name": "Ljubo",
                "patient_name": "Ana",
                "service": "Kontrola",
            }
        ]

    def time_off_for_week(self, week_start: date) -> list:
        self.time_off_for_week_calls += 1
        return []

    def breaks_for_week(self, week_start: date) -> list:
        self.breaks_for_week_calls += 1
        return []


class _FakeView:
    """View koji čuva dataset kroz ``render`` i računa counts iz njega."""

    DAY_COUNT = 6

    def __init__(self) -> None:
        self.render_calls = 0
        self.appointments: list = []
        self.blocks: list = []
        self.filter: int | None = None
        self.week_start: date | None = None
        self.day: date | None = None

    def render_schedule(self, appointments: list, blocks: list) -> None:
        self.render_calls += 1
        self.appointments = list(appointments)
        self.blocks = list(blocks)

    def visible_status_counts(self) -> dict[str, int]:
        return {"waiting": len(self.appointments)}

    def visible_doctor_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for appt in self.appointments:
            counts[appt["doctor_id"]] = counts.get(appt["doctor_id"], 0) + 1
        return counts

    def set_filter(self, doctor_id: int | None) -> None:
        self.filter = doctor_id

    def set_week_start(self, week_start: date) -> None:
        self.week_start = week_start

    def set_day(self, day: date) -> None:
        self.day = day


class _ViewStack:
    def __init__(self, week_view: _FakeView, day_view: _FakeView) -> None:
        self.week_view = week_view
        self.day_view = day_view
        self.current = week_view

    def currentWidget(self) -> _FakeView:
        return self.current


def _make_controller(
    store: _CountingStore | None = None,
) -> tuple[ScheduleController, _CountingStore, _FakeView, _FakeView, _ViewStack, list, list]:
    store = store or _CountingStore()
    week_view = _FakeView()
    day_view = _FakeView()
    view_stack = _ViewStack(week_view, day_view)
    status_counts: list[dict] = []
    doctor_counts: list[dict] = []
    controller = ScheduleController(
        store,
        week_view,
        day_view,
        view_stack,
        on_range_label=lambda: None,
        on_status_counts=status_counts.append,
        on_doctor_counts=doctor_counts.append,
        week_start=WEEK_START,
    )
    return controller, store, week_view, day_view, view_stack, status_counts, doctor_counts


def test_refresh_fetchuje_samo_jednom() -> None:
    controller, store, week_view, day_view, _, _, _ = _make_controller()

    controller.refresh()

    assert store.appointments_for_range_calls == 1
    assert store.time_off_for_week_calls == 1
    assert store.breaks_for_week_calls == 1
    assert week_view.render_calls == 1
    # Skriveni (neaktivan) view se ne renderuje.
    assert day_view.render_calls == 0


def test_refresh_renderuje_samo_aktivan_view() -> None:
    controller, store, week_view, day_view, view_stack, _, _ = _make_controller()

    controller.refresh()
    assert week_view.render_calls == 1
    assert day_view.render_calls == 0

    # Pređi na day view — sada se renderuje day, ne week.
    view_stack.current = day_view
    controller.refresh()
    assert day_view.render_calls == 1
    assert week_view.render_calls == 1  # i dalje 1 — nije renderovan drugi put


def test_counts_iz_istog_dataseta_bez_dodatnog_fetcha() -> None:
    controller, store, _, _, _, status_counts, doctor_counts = _make_controller()

    controller.refresh()

    assert status_counts == [{"waiting": 1}]
    assert doctor_counts == [{1: 1}]
    # Nema dodatnog fetch-a za counts — sve iz ISTOG render-ovanog dataseta.
    assert store.appointments_for_range_calls == 1


def test_move_week_povecava_week_start_i_refreshuje() -> None:
    controller, store, week_view, day_view, _, _, _ = _make_controller()
    original = controller.week_start

    controller.move_week(1)

    assert controller.week_start == original + timedelta(days=7)
    assert week_view.week_start == controller.week_start
    assert day_view.day == controller.week_start
    assert store.appointments_for_range_calls == 1


def test_set_doctor_filter_postavlja_filter_i_refreshuje() -> None:
    controller, store, week_view, _, _, _, _ = _make_controller()

    controller.set_doctor_filter(3)

    assert week_view.filter == 3
    assert store.appointments_for_range_calls == 1


def test_fetch_radi_sa_store_bez_appointments_for_range() -> None:
    """Fallback na ``store.all()`` kad nema range fetch-a (FakeStore obrazac)."""

    class LegacyStore:
        def __init__(self) -> None:
            self.all_calls = 0

        def all(self) -> list:
            self.all_calls += 1
            return []

        def time_off_for_week(self, week_start: date) -> list:
            return []

        def breaks_for_week(self, week_start: date) -> list:
            return []

    store = LegacyStore()
    controller, _, week_view, _, _, _, _ = _make_controller(store)

    controller.refresh()

    assert week_view.render_calls == 1
    assert week_view.appointments == []
    assert store.all_calls == 1
