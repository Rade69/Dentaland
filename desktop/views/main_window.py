"""Glavni prozor desktop aplikacije."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from dentaland import paths
from dentaland.services import OverlapError  # noqa: F401  # re-eksport (REF-00 baseline)
from dentaland.timezone import SARAJEVO
from desktop.controllers.appointment_controller import AppointmentController
from desktop.controllers.print_controller import PrintController
from desktop.controllers.schedule_controller import ScheduleController
from desktop.presentation.theme import apply_theme
from desktop.views.blockout_panel import BlockoutPanel
from desktop.views.day_view import DayView

# Re-eksport dijalog klasa: AppointmentController ih dohvata lazy importom
# (late binding), a postojeći GUI testovi monkeypatch-uju ih na ovom modulu.
from desktop.views.dialogs.appointment_details import AppointmentDetailsDialog  # noqa: F401
from desktop.views.dialogs.appointment_editor import AppointmentEditorDialog  # noqa: F401
from desktop.views.dialogs.cancel_appointment import CancelAppointmentDialog  # noqa: F401
from desktop.views.dialogs.delete_appointment import DeleteAppointmentDialog  # noqa: F401
from desktop.views.dialogs.move_appointment import MoveAppointmentDialog  # noqa: F401
from desktop.views.requests_page import RequestsPage
from desktop.views.requests_panel import DashboardPanels
from desktop.views.settings_panel import SettingsPanel
from desktop.views.sidebar import Sidebar, svg_icon
from desktop.views.stub_page import StubPage
from desktop.views.week_view import STATUS_META, STATUS_ORDER, WeekView

AUTO_REFRESH_INTERVAL_MS = 20_000
DOCTOR_PHOTO_FILES = {
    "Ljubo": "ljubo.png",
    "Zorka": "zorka.png",
    "Ana": "ana.png",
}
DOCTOR_AVATAR_SIZE = 56


def _circular_doctor_pixmap(doctor_name: str) -> QPixmap:
    """Učitaj lokalnu fotografiju doktora i isijeci je u kružni avatar."""
    filename = DOCTOR_PHOTO_FILES.get(doctor_name)
    if filename is None:
        return QPixmap()
    source = QPixmap(str(paths.resource_path("desktop", "assets", "doctors", filename)))
    if source.isNull():
        return source

    size = DOCTOR_AVATAR_SIZE
    scaled = source.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    avatar = QPixmap(size, size)
    avatar.fill(Qt.GlobalColor.transparent)
    painter = QPainter(avatar)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addEllipse(0, 0, size, size)
    painter.setClipPath(clip)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return avatar


class MainWindow(QMainWindow):
    """Sedmični raspored + filter tabovi doktora + alatna traka (štampa stub)."""

    def __init__(
        self,
        store: Any,
        week_start: date | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.store = store
        self._current_doctor_id: int | None = None
        self._has_doctors = False
        self._doctors: list = []
        self.setWindowTitle("Dentaland")
        self.setWindowIcon(QIcon(str(paths.resource_path("web", "assets", "logo.png"))))
        # Razumna restore veličina; entrypoint prozor otvara maksimizovan.
        # Starih 1536x1000 prelazilo je radnu visinu na Windowsu pri 125% DPI.
        self.resize(1280, 720)

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        self.week_view = WeekView(store, week_start, parent=self)
        self.day_view = DayView(store, date.today(), parent=self)
        self._controller = AppointmentController(store, self, self._refresh_dashboard)
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.week_view)
        self.view_stack.addWidget(self.day_view)
        self._schedule_controller = ScheduleController(
            store,
            self.week_view,
            self.day_view,
            self.view_stack,
            on_range_label=self._update_range_label,
            on_status_counts=self._set_status_counts,
            on_doctor_counts=self._set_doctor_counts,
            week_start=week_start,
        )
        self.week_view.appointment_moved.connect(
            lambda _appt: self._schedule_controller.refresh()
        )
        self.day_view.appointment_moved.connect(
            lambda _appt: self._schedule_controller.refresh()
        )
        self._print_controller = PrintController(
            store, self, lambda: self._schedule_controller.week_start
        )
        self.doctor_tabs = self._build_doctor_tabs()
        self.sidebar = Sidebar(self)
        self.dashboard_panels = DashboardPanels(store, self)
        self.dashboard_panels.changed.connect(self._refresh_dashboard)
        self.sidebar.route_selected.connect(self._show_route)

        self.page_stack = QStackedWidget()
        self.schedule_page = self._build_schedule_page()
        self.page_stack.addWidget(self.schedule_page)
        self._route_pages: dict[str, QWidget] = {"raspored": self.schedule_page}
        for route, title in (
            ("pacijenti", "Pacijenti"),
            ("izvjestaji", "Izvještaji"),
            ("podsjetnici", "Podsjetnici"),
        ):
            page = StubPage(title)
            self._route_pages[route] = page
            self.page_stack.addWidget(page)
        self.requests_page = RequestsPage(store, self)
        self.requests_page.changed.connect(self._refresh_dashboard)
        self._route_pages["zahtjevi"] = self.requests_page
        self.page_stack.addWidget(self.requests_page)
        self.blockout_panel = BlockoutPanel(store, self)
        self.blockout_panel.changed.connect(self._refresh_dashboard)
        self._route_pages["blockout"] = self.blockout_panel
        self.page_stack.addWidget(self.blockout_panel)
        self.settings_panel = SettingsPanel(store, self)
        self.settings_panel.changed.connect(self._refresh_dashboard)
        self._route_pages["postavke"] = self.settings_panel
        self.page_stack.addWidget(self.settings_panel)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.sidebar)
        root.addWidget(self.page_stack, 1)
        self.setCentralWidget(central)

        self.print_action = QAction("Štampaj raspored", self)
        self.print_action.triggered.connect(self._print_controller.on_print)
        self.addAction(self.print_action)

        self.week_view.slot_selected.connect(self._controller.on_slot_selected)
        self.week_view.appointment_clicked.connect(self._controller.open_appointment_details)
        self.week_view.appointment_action_requested.connect(self._controller.handle_appointment_action)
        self.day_view.slot_selected.connect(self._controller.on_slot_selected)
        self.day_view.appointment_clicked.connect(self._controller.open_appointment_details)
        self.day_view.appointment_action_requested.connect(self._controller.handle_appointment_action)
        self._apply_style()
        self._refresh_dashboard()

        # Novi zahtjevi sa web forme (drugi proces, druga konekcija na istu
        # bazu) se inače vide tek poslije ručnog restarta aplikacije —
        # periodično osvježavanje umjesto toga.
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(AUTO_REFRESH_INTERVAL_MS)
        self._auto_refresh_timer.timeout.connect(self._refresh_dashboard)
        self._auto_refresh_timer.start()

    @property
    def week_start(self) -> date:
        """Prikazani početak sedmice — izvor istine je ScheduleController."""
        return self._schedule_controller.week_start

    def _build_schedule_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("schedulePage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 18, 14, 14)
        layout.setSpacing(13)

        header_frame = QFrame()
        header_frame.setObjectName("topHeader")
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(0, 0, 0, 14)
        header.setSpacing(10)
        title_column = QVBoxLayout()
        title_column.setSpacing(1)
        title = QLabel("Raspored termina")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Sedmični pregled zakazanih termina")
        subtitle.setObjectName("pageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header.addLayout(title_column)
        header.addStretch()
        today_button = QPushButton("Danas")
        today_button.setObjectName("todayButton")
        previous = QPushButton("‹")
        previous.setObjectName("navArrow")
        following = QPushButton("›")
        following.setObjectName("navArrow")
        self.range_label = QLabel()
        self.range_label.setObjectName("rangeLabel")
        self.range_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        today_button.clicked.connect(self._go_today)
        previous.clicked.connect(lambda: self._move_week(-1))
        following.clicked.connect(lambda: self._move_week(1))
        header.addWidget(today_button)
        header.addWidget(previous)
        header.addWidget(following)
        header.addWidget(self.range_label)
        self.day_button = QPushButton("Dan")
        self.day_button.setObjectName("viewSegment")
        self.day_button.setCheckable(True)
        self.day_button.clicked.connect(self._show_day_view)
        self.week_button = QPushButton("Sedmica")
        self.week_button.setObjectName("viewSegment")
        self.week_button.setCheckable(True)
        self.week_button.setChecked(True)
        self.week_button.clicked.connect(self._show_week_view)
        header.addWidget(self.day_button)
        header.addWidget(self.week_button)
        new_button = QPushButton("Novi termin")
        new_button.setObjectName("primaryButton")
        new_button.setIcon(svg_icon("plus", "#ffffff", 18))
        new_button.setIconSize(QSize(18, 18))
        new_button.clicked.connect(self._on_new_appointment)
        print_button = QPushButton("Štampa  ⌄")
        print_button.setObjectName("printButton")
        print_button.setIcon(svg_icon("printer", "#10213d", 18))
        print_button.setIconSize(QSize(18, 18))
        print_button.clicked.connect(self._print_controller.on_print)
        header.addWidget(new_button)
        header.addWidget(print_button)
        layout.addWidget(header_frame)

        filter_frame = QFrame()
        filter_frame.setObjectName("filterBar")
        filters = QHBoxLayout(filter_frame)
        filters.setContentsMargins(0, 0, 0, 0)
        filters.setSpacing(8)
        filters.addWidget(QLabel("Doktor"))
        if self.doctor_tabs is not None:
            filters.addWidget(self.doctor_tabs)
        filters.addStretch()
        layout.addWidget(filter_frame)

        content = QHBoxLayout()
        content.setSpacing(14)
        calendar_column = QVBoxLayout()
        calendar_column.setSpacing(10)
        calendar_column.addWidget(self.view_stack, 1)
        self.status_legend = QLabel()
        self.status_legend.setObjectName("statusLegend")
        self.status_legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_legend.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        self.status_legend.setFixedHeight(48)
        calendar_column.addWidget(self.status_legend)
        content.addLayout(calendar_column, 1)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(6)
        self.doctor_legend = QFrame()
        self.doctor_legend.setObjectName("doctorLegend")
        legend_layout = QVBoxLayout(self.doctor_legend)
        legend_layout.setContentsMargins(12, 10, 12, 10)
        legend_layout.setSpacing(7)
        legend_title = QLabel("Doktori")
        legend_title.setObjectName("doctorLegendTitle")
        legend_layout.addWidget(legend_title)
        self._doctor_badge_labels = {}
        for index, doctor in enumerate(self._doctors):
            color = WeekView._DOCTOR_PALETTE[index % len(WeekView._DOCTOR_PALETTE)]
            row = QWidget()
            row.setObjectName("doctorLegendRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(9)

            avatar = QLabel()
            avatar.setObjectName(f"doctorAvatar{doctor.ime}")
            avatar.setFixedSize(DOCTOR_AVATAR_SIZE, DOCTOR_AVATAR_SIZE)
            avatar.setPixmap(_circular_doctor_pixmap(doctor.ime))
            row_layout.addWidget(avatar)

            name = QLabel(f"Dr {doctor.ime}")
            name.setObjectName("doctorLegendName")
            row_layout.addWidget(name, 1)

            badge = QLabel("0")
            badge.setObjectName("doctorLegendBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(24, 24)
            badge.setStyleSheet(
                f"background-color: {color}; color: #ffffff; font-weight: 700; "
                f"border-radius: 12px; font-size: 12px;"
            )
            self._doctor_badge_labels[doctor.id] = badge
            row_layout.addWidget(badge)
            legend_layout.addWidget(row)
        self.doctor_legend.setVisible(bool(self._doctors))
        right_column.addWidget(self.doctor_legend)
        right_column.addWidget(self.dashboard_panels, 1)
        content.addLayout(right_column)
        layout.addLayout(content, 1)
        self._update_range_label()
        return page

    def _show_route(self, route: str) -> None:
        page = self._route_pages.get(route)
        if page is not None:
            if page is self.requests_page:
                self.requests_page.refresh()
            self.page_stack.setCurrentWidget(page)

    def _move_week(self, offset: int) -> None:
        self._schedule_controller.move_week(offset)

    def _go_today(self) -> None:
        self._schedule_controller.go_today()

    def _show_day_view(self) -> None:
        self.view_stack.setCurrentWidget(self.day_view)
        self.day_button.setChecked(True)
        self.week_button.setChecked(False)
        self._schedule_controller.show_day_view()

    def _show_week_view(self) -> None:
        self.view_stack.setCurrentWidget(self.week_view)
        self.week_button.setChecked(True)
        self.day_button.setChecked(False)
        self._schedule_controller.show_week_view()

    def _update_range_label(self) -> None:
        end = self._schedule_controller.week_start + timedelta(days=5)
        months = [
            "januar", "februar", "mart", "april", "maj", "juni",
            "juli", "avgust", "septembar", "oktobar", "novembar", "decembar",
        ]
        if self._schedule_controller.week_start.month == end.month:
            text = (
                f"{self._schedule_controller.week_start.day} – {end.day}. "
                f"{months[end.month - 1]} {end.year}"
            )
        else:
            text = f"{self._schedule_controller.week_start:%d.%m.} – {end:%d.%m.%Y}"
        self.range_label.setText(f"▣   {text}   ▣")

    def _refresh_dashboard(self) -> None:
        self.dashboard_panels.refresh()
        self.requests_page.refresh()
        pending = getattr(self.store, "pending_requests", None)
        count = len(pending()) if callable(pending) else 0
        self.sidebar.set_pending_count(count)
        self._schedule_controller.refresh()

    def _set_status_counts(self, counts: dict[str, int]) -> None:
        legend_html = "&nbsp;".join(
            f"<span style='color:{STATUS_META[key][1]}; font-size:10px; "
            f"font-weight:700'>{STATUS_META[key][0]}</span>&nbsp;"
            f"<span style='font-size:10px'>{STATUS_META[key][2]} ({counts[key]})</span>"
            for key in STATUS_ORDER
        )
        self.status_legend.setText(legend_html)

    def _set_doctor_counts(self, counts: dict[int, int]) -> None:
        for doctor_id, label in self._doctor_badge_labels.items():
            label.setText(str(counts.get(doctor_id, 0)))

    def _on_new_appointment(self) -> None:
        now = datetime.now(SARAJEVO)
        start = now.replace(second=0, microsecond=0)
        start += timedelta(minutes=(-start.minute) % 30)
        self._controller.on_slot_selected(start)

    # Tanke delegacije ka Controller-u — zadržane radi backward-compat
    # postojećih GUI testova koji pozivaju ove privatne metode direktno.
    # Implementacija workflow-a živi u AppointmentController, ne ovdje.
    def _handle_appointment_action(self, appt_id: int, action: str) -> None:
        self._controller.handle_appointment_action(appt_id, action)

    def _cancel_appointment(self, appt: Any) -> None:
        self._controller.cancel_appointment(appt)

    def _delete_appointment(self, appt: Any) -> None:
        self._controller.delete_appointment(appt)

    def _apply_style(self) -> None:
        apply_theme(self)

    def _build_doctor_tabs(self) -> QTabBar | None:
        doctors_fn = getattr(self.store, "doctors", None)
        if not callable(doctors_fn):
            return None
        self._doctors = list(doctors_fn())
        self._has_doctors = bool(self._doctors)
        if not self._doctors:
            return None
        tabs = QTabBar()
        tabs.addTab("Svi doktori")
        for doctor in self._doctors:
            tabs.addTab(doctor.ime)
        self._tab_doctor_ids: list[int | None] = [None] + [d.id for d in self._doctors]
        tabs.currentChanged.connect(self._on_tab_changed)
        return tabs

    def _on_tab_changed(self, index: int) -> None:
        doctor_id = self._tab_doctor_ids[index]
        self._current_doctor_id = doctor_id
        self._schedule_controller.set_doctor_filter(doctor_id)
