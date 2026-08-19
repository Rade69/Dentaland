"""Glavni prozor desktop aplikacije."""

from __future__ import annotations

from contextlib import suppress
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from dentaland.services import OverlapError
from dentaland.services.print_schedule import build_day_schedule, build_week_schedule
from desktop.fake_data import SARAJEVO
from desktop.print_document import build_day_document, build_week_document, preview_document
from desktop.views.day_view import DayView
from desktop.views.dialogs.appointment_details import AppointmentDetailsDialog
from desktop.views.dialogs.appointment_editor import AppointmentEditorDialog
from desktop.views.dialogs.cancel_appointment import CancelAppointmentDialog
from desktop.views.dialogs.delete_appointment import DeleteAppointmentDialog
from desktop.views.dialogs.move_appointment import MoveAppointmentDialog
from desktop.views.requests_panel import DashboardPanels
from desktop.views.sidebar import Sidebar, svg_icon
from desktop.views.stub_page import StubPage
from desktop.views.week_view import STATUS_META, STATUS_ORDER, WeekView

DEFAULT_MANUAL_DURATION_MINUTES = 60
AUTO_REFRESH_INTERVAL_MS = 20_000


class MainWindow(QMainWindow):
    """Sedmični raspored + filter tabovi doktora + alatna traka (štampa stub)."""

    def __init__(self, store, week_start: date | None = None, parent=None):
        super().__init__(parent)
        self.store = store
        self._current_doctor_id: int | None = None
        self._has_doctors = False
        self._doctors: list = []
        self.setWindowTitle("Dentaland")
        self.setWindowIcon(
            QIcon(str(Path(__file__).resolve().parents[2] / "web" / "assets" / "logo.png"))
        )
        # Razumna restore veličina; entrypoint prozor otvara maksimizovan.
        # Starih 1536x1000 prelazilo je radnu visinu na Windowsu pri 125% DPI.
        self.resize(1280, 720)

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        self.current_day = date.today()
        self.week_start = week_start
        self.week_view = WeekView(store, week_start, parent=self)
        self.day_view = DayView(store, self.current_day, parent=self)
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.week_view)
        self.view_stack.addWidget(self.day_view)
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
            ("zahtjevi", "Novi zahtjevi"),
            ("pacijenti", "Pacijenti"),
            ("izvjestaji", "Izvještaji"),
            ("postavke", "Postavke"),
            ("blockout", "Blokiraj vrijeme"),
            ("podsjetnici", "Podsjetnici"),
        ):
            page = StubPage(title)
            self._route_pages[route] = page
            self.page_stack.addWidget(page)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.sidebar)
        root.addWidget(self.page_stack, 1)
        self.setCentralWidget(central)

        self.print_action = QAction("Štampaj raspored", self)
        self.print_action.triggered.connect(self._on_print)
        self.addAction(self.print_action)

        self.week_view.slot_selected.connect(self._on_slot_selected)
        self.week_view.appointment_clicked.connect(self._open_appointment_details)
        self.week_view.appointment_action_requested.connect(self._handle_appointment_action)
        self.day_view.slot_selected.connect(self._on_slot_selected)
        self.day_view.appointment_clicked.connect(self._open_appointment_details)
        self.day_view.appointment_action_requested.connect(self._handle_appointment_action)
        self._apply_style()
        self._refresh_dashboard()

        # Novi zahtjevi sa web forme (drugi proces, druga konekcija na istu
        # bazu) se inače vide tek poslije ručnog restarta aplikacije —
        # periodično osvježavanje umjesto toga.
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(AUTO_REFRESH_INTERVAL_MS)
        self._auto_refresh_timer.timeout.connect(self._refresh_dashboard)
        self._auto_refresh_timer.start()

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
        print_button.clicked.connect(self._on_print)
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
        legend_layout = QHBoxLayout(self.doctor_legend)
        legend_layout.setContentsMargins(10, 0, 0, 0)
        legend_layout.setSpacing(10)
        for index, doctor in enumerate(self._doctors):
            color = WeekView._DOCTOR_PALETTE[index % len(WeekView._DOCTOR_PALETTE)]
            label = QLabel(f"● Dr {doctor.ime}")
            label.setStyleSheet(f"color: {color}; font-weight: 600;")
            legend_layout.addWidget(label)
        legend_layout.addStretch()
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
            self.page_stack.setCurrentWidget(page)

    def _move_week(self, offset: int) -> None:
        if self.view_stack.currentWidget() is self.day_view:
            self.current_day += timedelta(days=offset)
            self.day_view.set_day(self.current_day)
        else:
            self.week_start += timedelta(days=7 * offset)
            self.week_view.set_week_start(self.week_start)
            self.day_view.set_day(self.week_start)
        self._update_range_label()
        self._update_status_legend()

    def _go_today(self) -> None:
        today = date.today()
        if self.view_stack.currentWidget() is self.day_view:
            self.current_day = today
            self.day_view.set_day(self.current_day)
        else:
            self.week_start = today - timedelta(days=today.weekday())
            self.week_view.set_week_start(self.week_start)
            self.day_view.set_day(self.week_start)
        self._update_range_label()
        self._update_status_legend()

    def _show_day_view(self) -> None:
        self.day_view.set_day(self.current_day)
        self.view_stack.setCurrentWidget(self.day_view)
        self.day_button.setChecked(True)
        self.week_button.setChecked(False)
        self._update_status_legend()

    def _show_week_view(self) -> None:
        self.view_stack.setCurrentWidget(self.week_view)
        self.week_button.setChecked(True)
        self.day_button.setChecked(False)
        self._update_status_legend()

    def _update_range_label(self) -> None:
        end = self.week_start + timedelta(days=5)
        months = [
            "januar", "februar", "mart", "april", "maj", "juni",
            "juli", "avgust", "septembar", "oktobar", "novembar", "decembar",
        ]
        if self.week_start.month == end.month:
            text = f"{self.week_start.day} – {end.day}. {months[end.month - 1]} {end.year}"
        else:
            text = f"{self.week_start:%d.%m.} – {end:%d.%m.%Y}"
        self.range_label.setText(f"▣   {text}   ▣")

    def _refresh_dashboard(self) -> None:
        self.dashboard_panels.refresh()
        self.week_view.refresh()
        self.day_view.refresh()
        pending = getattr(self.store, "pending_requests", None)
        count = len(pending()) if callable(pending) else 0
        self.sidebar.set_pending_count(count)
        self._update_status_legend()

    def _update_status_legend(self) -> None:
        view = self.view_stack.currentWidget()
        counts_fn = getattr(view, "visible_status_counts", None)
        counts = counts_fn() if callable(counts_fn) else dict.fromkeys(STATUS_META, 0)
        legend_html = "&nbsp;&nbsp;&nbsp;&nbsp;".join(
            f"<span style='color:{STATUS_META[key][1]}; font-size:14px; "
            f"font-weight:700'>{STATUS_META[key][0]}</span>&nbsp; "
            f"{STATUS_META[key][2]} ({counts[key]})"
            for key in STATUS_ORDER
        )
        self.status_legend.setText(legend_html)

    def _on_new_appointment(self) -> None:
        now = datetime.now(SARAJEVO)
        start = now.replace(second=0, microsecond=0)
        start += timedelta(minutes=(-start.minute) % 30)
        self._on_slot_selected(start)

    def _apply_style(self) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#10213d"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7fafc"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#10213d"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#10213d"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#078f96"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#718096"))
            app.setPalette(palette)
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #ffffff;
                color: #10213d;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QMainWindow { border: 0; }
            #sidebar {
                background-color: #fbfdfe;
                border-right: 1px solid #d9e3ea;
            }
            #sidebarNavigation, #sidebarNavigationBody,
            #sidebarNavigation > QWidget > QWidget {
                background-color: #fbfdfe;
                border: 0;
            }
            #sidebarBrand { background: transparent; }
            #sidebarWordmark { color: #078f96; font-size: 10px; font-weight: 600; }
            #quickTitle { font-size: 15px; font-weight: 700; padding: 8px; }
            #sidebarStaff {
                border-top: 1px solid #d9e3ea;
                background: transparent;
            }
            #staffAvatar {
                background-color: #078f96;
                color: #ffffff;
                border-radius: 19px;
                font-weight: 600;
            }
            #pendingBadge {
                min-width: 23px;
                max-width: 23px;
                min-height: 23px;
                max-height: 23px;
                border-radius: 11px;
                background-color: #f02d4f;
                color: #ffffff;
                font-weight: 700;
            }
            #topHeader { border-bottom: 1px solid #e1e9ef; }
            #pageTitle { font-size: 18px; font-weight: 700; }
            #pageSubtitle { color: #31578a; font-size: 12px; }
            #rangeLabel {
                border: 1px solid #cad8e2;
                border-radius: 7px;
                min-width: 170px;
                min-height: 38px;
                font-weight: 600;
            }
            #primaryButton {
                background-color: #078f96;
                color: #ffffff;
                border: 1px solid #078f96;
                min-width: 110px;
            }
            QPushButton {
                background-color: #ffffff;
                color: #10213d;
                border: 1px solid #cad8e2;
                border-radius: 6px;
                min-height: 34px;
                padding: 2px 12px;
            }
            QPushButton:hover { background-color: #eef8f9; border-color: #078f96; }
            QPushButton:checked { background-color: #078f96; color: #ffffff; }
            QPushButton:disabled { background-color: #f5f7f9; color: #94a3b8; }
            QPushButton[nav="true"] {
                border: 0;
                text-align: left;
                min-height: 42px;
                padding: 7px 12px;
                font-size: 14px;
            }
            QPushButton[nav="true"]:hover { background-color: #eaf6f7; }
            QPushButton[nav="true"][active="true"] {
                background-color: #dff4f3;
                color: #086a73;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton[nav="true"][quick="true"] { min-height: 36px; }
            #navArrow { min-width: 34px; max-width: 34px; padding: 0; font-size: 20px; }
            #todayButton { min-width: 55px; font-weight: 600; }
            #viewSegment { min-width: 55px; }
            #printButton { min-width: 85px; font-weight: 600; }
            #statusLegend {
                background-color: #f4fafb;
                border: 1px solid #c9dce3;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QGroupBox {
                background-color: #ffffff;
                font-weight: 700;
                border: 1px solid #d9e3ea;
                border-radius: 9px;
                margin-top: 16px;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                top: -3px;
                padding: 0 5px;
                background-color: #ffffff;
            }
            #doctorLegend { background-color: #ffffff; min-height: 26px; }
            #dashboardPanels, #dashboardPanelContent { background-color: #ffffff; }
            #dashboardBox { font-size: 12px; }
            #dashboardBox QLabel { font-size: 11px; font-weight: 400; }
            #dashboardListItem {
                border-bottom: 1px solid #edf1f4;
                padding: 3px 1px 7px 1px;
            }
            #confirmButton, #rejectButton {
                min-height: 25px;
                max-height: 25px;
                padding: 0 7px;
                font-size: 10px;
            }
            #confirmButton { color: #078f96; border-color: #59c7ca; }
            #rejectButton { color: #ef334f; border-color: #ff8ba0; }
            #nextFreePlaceholder { color: #31578a; padding: 4px 0; }
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fbfc;
                color: #10213d;
                border: 1px solid #d9e3ea;
                gridline-color: #e5edf2;
                selection-background-color: #d9f1f2;
                selection-color: #10213d;
            }
            QHeaderView::section {
                background-color: #f7fafc;
                color: #42526b;
                border: 0;
                border-right: 1px solid #e5edf2;
                border-bottom: 1px solid #d9e3ea;
                padding: 6px;
            }
            QTableCornerButton::section { background-color: #f7fafc; }
            QTabBar::tab {
                background-color: #ffffff;
                color: #42526b;
                border: 1px solid #cad8e2;
                border-radius: 6px;
                padding: 8px 16px;
                margin-right: 4px;
                font-weight: 600;
            }
            QTabBar::tab:selected { background-color: #078f96; color: #ffffff; }
            QScrollArea, QScrollArea > QWidget > QWidget {
                background-color: #ffffff;
                border: 0;
            }
            QScrollBar:vertical { background: #f4f7f9; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: #bdcbd5; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QLineEdit, QComboBox, QDateTimeEdit {
                background-color: #ffffff;
                color: #10213d;
                border: 1px solid #cad8e2;
                border-radius: 5px;
                min-height: 30px;
                padding: 2px 8px;
            }
            """
        )

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
        self.week_view.set_filter(doctor_id)
        self._update_status_legend()

    def _service_options(self) -> list[tuple[str, int]]:
        """Usluge kao ``(naziv, trajanje_min)`` — iz store-a, sa legacy fallback-om."""
        fn = getattr(self.store, "service_options", None)
        if callable(fn):
            return [(o.naziv, o.trajanje_min) for o in fn()]
        services = getattr(self.store, "services", None)
        if callable(services):
            return [(name, DEFAULT_MANUAL_DURATION_MINUTES) for name in services()]
        return []

    def _on_slot_selected(self, start) -> None:
        dialog = AppointmentEditorDialog(
            [(d.id, d.ime) for d in self._doctors],
            self._service_options(),
            start,
            selected_doctor_id=self._current_doctor_id,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            data = dialog.get_data()
            doctor_id = data["doctor_id"]
            if self._has_doctors and doctor_id is None:
                dialog.show_error("Izaberite doktora.")
                continue
            end = data["start"] + timedelta(minutes=data["duration_min"])
            if doctor_id is not None and hasattr(self.store, "set_doctor"):
                self.store.set_doctor(doctor_id)
            try:
                self.store.create(
                    patient_name=data["patient_name"],
                    phone=data["phone"],
                    email=data["email"],
                    service=data["service"],
                    note=data["note"],
                    start=data["start"],
                    end=end,
                )
                break
            except OverlapError as exc:
                dialog.show_error(str(exc))
        self._refresh_dashboard()

    def _edit_appointment(self, appt: Any) -> None:
        """Otvori editor u edit modu i sačuvaj kroz ``store.update``.

        Ožičava se iz ``Detalji termina`` u Fazi C — ovdje je pripremljena
        ulazna tačka (i testirana) da editor već podržava edit.
        """
        dialog = AppointmentEditorDialog(
            [(d.id, d.ime) for d in self._doctors],
            self._service_options(),
            appt.start,
            appointment=appt,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            data = dialog.get_data()
            doctor_id = data["doctor_id"]
            if self._has_doctors and doctor_id is None:
                dialog.show_error("Izaberite doktora.")
                continue
            end = data["start"] + timedelta(minutes=data["duration_min"])
            update_fn = getattr(self.store, "update", None)
            if not callable(update_fn):
                dialog.show_error("Uređivanje nije podržano za ovaj izvor podataka.")
                continue
            try:
                update_fn(
                    appt.id,
                    patient_name=data["patient_name"],
                    phone=data["phone"],
                    email=data["email"],
                    doctor_id=doctor_id,
                    service=data["service"],
                    note=data["note"],
                    start=data["start"],
                    end=end,
                )
                break
            except OverlapError as exc:
                dialog.show_error(str(exc))
        self._refresh_dashboard()

    def _open_appointment_details(self, appt_id: int) -> None:
        appt = self.store.get(appt_id)
        if appt is None:
            return
        dialog = AppointmentDetailsDialog(appt, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            action = dialog.selected_action()
            if action is not None:
                self._handle_appointment_action(appt_id, action)

    def _handle_appointment_action(self, appt_id: int, action: str) -> None:
        if action == "open_details":
            self._open_appointment_details(appt_id)
            return
        if action == "edit":
            appt = self.store.get(appt_id)
            if appt is not None:
                self._edit_appointment(appt)
            return
        if action == "move":
            appt = self.store.get(appt_id)
            if appt is not None:
                self._move_appointment(appt)
            return
        if action == "cancel":
            appt = self.store.get(appt_id)
            if appt is not None:
                self._cancel_appointment(appt)
            return
        if action == "delete":
            appt = self.store.get(appt_id)
            if appt is not None:
                self._delete_appointment(appt)
            return
        method_map = {
            "confirm": "mark_confirmed",
            "arrived": "mark_arrived",
            "unarrived": "unmark_arrived",
            "completed": "mark_completed",
            "no_show": "mark_no_show",
        }
        method_name = method_map.get(action)
        if method_name is None:
            return
        method = getattr(self.store, method_name, None)
        if callable(method):
            with suppress(ValueError):
                method(appt_id)
        self._refresh_dashboard()

    def _move_appointment(self, appt: Any) -> None:
        dialog = MoveAppointmentDialog(appt, self)
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            new_start, duration_min = dialog.get_data()
            new_end = new_start + timedelta(minutes=duration_min)
            try:
                self.store.move(appt.id, new_start, new_end)
                break
            except OverlapError as exc:
                dialog.show_error(str(exc))
        self._refresh_dashboard()

    def _cancel_appointment(self, appt: Any) -> None:
        dialog = CancelAppointmentDialog(appt, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cancel_fn = getattr(self.store, "cancel", None)
            if callable(cancel_fn):
                with suppress(ValueError):
                    cancel_fn(appt.id)
            self._refresh_dashboard()

    def _delete_appointment(self, appt: Any) -> None:
        """Trajno ukloni termin (Faza F, HIGH) — nepovratno, odvojeno od cancel."""
        dialog = DeleteAppointmentDialog(appt, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            delete_fn = getattr(self.store, "delete", None)
            if callable(delete_fn):
                with suppress(ValueError):
                    delete_fn(appt.id)
            self._refresh_dashboard()

    def _on_print(self) -> None:
        menu = QMenu(self)
        week_action = menu.addAction("Štampaj prikazanu sedmicu")
        day_action = menu.addAction("Štampaj jedan dan…")
        pdf_action = menu.addAction("Sačuvaj kao PDF")
        chosen = menu.exec(QCursor.pos())
        if chosen == week_action:
            self._print_week()
        elif chosen == day_action:
            self._print_day()
        elif chosen == pdf_action:
            self._save_pdf()

    def _print_week(self) -> None:
        schedule = build_week_schedule(self.store, self.week_start)
        preview_document(self, build_week_document(schedule), landscape=True)

    def _print_day(self) -> None:
        day = self._pick_day()
        if day is None:
            return
        schedule = build_day_schedule(self.store, day)
        preview_document(self, build_day_document(schedule), landscape=False)

    def _save_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Sačuvaj raspored kao PDF", "raspored.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        schedule = build_week_schedule(self.store, self.week_start)
        preview_document(
            self, build_week_document(schedule), landscape=True, pdf_path=path
        )

    def _pick_day(self) -> date | None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Izaberite dan za štampu")
        calendar = QCalendarWidget(dialog)
        calendar.setSelectedDate(
            QDate(self.week_start.year, self.week_start.month, self.week_start.day)
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout = QVBoxLayout(dialog)
        layout.addWidget(calendar)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        selected = calendar.selectedDate()
        return date(selected.year(), selected.month(), selected.day())
