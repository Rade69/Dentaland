"""Schedule controller (REF-05).

Preuzima iz ``MainWindow``: Day/Week state, current date/week, doctor filter,
schedule refresh, status summary i doctor counts. View prestaje fetch-ovati
— controller fetch-uje JEDAN snapshot po refresh-u (jedan
``appointments_for_range`` + jedan ``time_off_for_week``/``breaks_for_week``)
i prosleđuje ga aktivnom view-u kroz ``render(appointments, blocks)``.
Status summary i doctor counts idu iz ISTOG dataseta — view ih računa iz
cache-a koji je ``render`` postavio, ne fetch-uje ponovo.

Pravila sloja (plan sekcija 3.2): Controller SMIJE uvoziti PySide6, ali NE
smije crtati widgete niti raditi SQL — sav pristup podacima ide kroz
``store`` (facade). ``view_stack.currentWidget()`` se samo ČITA da bi se
odredio aktivan view.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from PySide6.QtWidgets import QStackedWidget

from dentaland.timezone import SARAJEVO
from desktop.views.day_view import DayView
from desktop.views.week_view import WeekView


class ScheduleController:
    """Koordinacija scheduler state-a i refresh-a, nezavisna od ``MainWindow``."""

    def __init__(
        self,
        store: Any,
        week_view: WeekView,
        day_view: DayView,
        view_stack: QStackedWidget,
        *,
        on_range_label: Callable[[], None],
        on_status_counts: Callable[[dict[str, int]], None],
        on_doctor_counts: Callable[[dict[int, int]], None],
        week_start: date | None = None,
    ) -> None:
        self._store = store
        self._week_view = week_view
        self._day_view = day_view
        self._view_stack = view_stack
        self._on_range_label = on_range_label
        self._on_status_counts = on_status_counts
        self._on_doctor_counts = on_doctor_counts

        today = date.today()
        self.week_start = week_start or (today - timedelta(days=today.weekday()))
        self.current_day = today

    # --- aktivan view ---

    def _active_view(self) -> Any:
        return self._view_stack.currentWidget()

    def _is_day_active(self) -> bool:
        return self._active_view() is self._day_view

    # --- fetch (jedan snapshot po refresh-u) ---

    def _active_range(self) -> tuple[datetime, datetime]:
        if self._is_day_active():
            day = self.current_day
            start = datetime(day.year, day.month, day.day, tzinfo=SARAJEVO)
            return start, start + timedelta(days=1)
        week_start = self.week_start
        start = datetime(week_start.year, week_start.month, week_start.day, tzinfo=SARAJEVO)
        return start, start + timedelta(days=self._week_view.DAY_COUNT)

    def _fetch_appointments(self) -> list[Any]:
        fetch = getattr(self._store, "appointments_for_range", None)
        if callable(fetch):
            start, end = self._active_range()
            return fetch(start, end)
        all_fn = getattr(self._store, "all", None)
        return list(all_fn()) if callable(all_fn) else []

    def _blocks_week_start(self) -> date:
        if self._is_day_active():
            return self.current_day - timedelta(days=self.current_day.weekday())
        return self.week_start

    def _fetch_blocks(self) -> list[Any]:
        week_start = self._blocks_week_start()
        blocks: list[Any] = []
        for method_name in ("time_off_for_week", "breaks_for_week"):
            method = getattr(self._store, method_name, None)
            if callable(method):
                blocks.extend(method(week_start))
        return blocks

    # --- refresh ---

    def refresh(self) -> None:
        view = self._active_view()
        snapshot = getattr(self._store, "schedule_snapshot", None)
        if callable(snapshot):
            start, end = self._active_range()
            appointments, blocks = snapshot(start, end, self._blocks_week_start())
        else:
            appointments = self._fetch_appointments()
            blocks = self._fetch_blocks()
        view.render_schedule(appointments, blocks)
        self._on_status_counts(view.visible_status_counts())
        self._on_doctor_counts(view.visible_doctor_counts())

    # --- state transitions ---

    def move_week(self, offset: int) -> None:
        if self._is_day_active():
            self.current_day += timedelta(days=offset)
            self._day_view.set_day(self.current_day)
        else:
            self.week_start += timedelta(days=7 * offset)
            self._week_view.set_week_start(self.week_start)
            self._day_view.set_day(self.week_start)
        self._on_range_label()
        self.refresh()

    def go_today(self) -> None:
        today = date.today()
        if self._is_day_active():
            self.current_day = today
            self._day_view.set_day(self.current_day)
        else:
            self.week_start = today - timedelta(days=today.weekday())
            self._week_view.set_week_start(self.week_start)
            self._day_view.set_day(self.week_start)
        self._on_range_label()
        self.refresh()

    def show_day_view(self) -> None:
        self._day_view.set_day(self.current_day)
        self.refresh()

    def show_week_view(self) -> None:
        self.refresh()

    def set_doctor_filter(self, doctor_id: int | None) -> None:
        self._week_view.set_filter(doctor_id)
        self.refresh()
