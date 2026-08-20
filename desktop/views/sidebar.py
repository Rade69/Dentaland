"""Lijeva navigacija Dentaland desktop dashboarda."""

from PySide6.QtCore import QByteArray, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dentaland import paths

_ICON_PATHS = {
    "calendar": (
        '<rect x="3" y="4.5" width="18" height="16.5" rx="2"/>'
        '<path d="M8 2.5v4M16 2.5v4M3 9h18"/>'
    ),
    "bell": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20V7M2 20h22"/>',
    "settings": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M20 12a8 8 0 0 0-.2-1.8l2-1.5-2-3.4-2.5 1a8 8 0 0 0-3.1-1.8'
        'L14 2h-4l-.3 2.5a8 8 0 0 0-3.1 1.8l-2.4-1-2 3.4 2 1.5A8 8 0 0 0 4 12'
        'c0 .6.1 1.2.2 1.8l-2 1.5 2 3.4 2.4-1a8 8 0 0 0 3.1 1.8L10 22h4l.3-2.5'
        'a8 8 0 0 0 3.1-1.8l2.5 1 2-3.4-2-1.5c.1-.6.1-1.2.1-1.8Z"/>'
    ),
    "user-plus": (
        '<circle cx="9" cy="8" r="4"/>'
        '<path d="M2 21c0-4 3-7 7-7 2 0 3.7.7 5 1.8M19 8v6M16 11h6"/>'
    ),
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "printer": (
        '<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5'
        'a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="7" rx="1"/>'
    ),
    "tooth": (
        '<path d="M12 2.5C8 1.4 4.8 4 5 8.2c.2 3.2 2 4.1 2.5 8.3.5 4.2 '
        '2.2 5.7 3.3 1.6L12 14l1.2 4.1c1.1 4.1 2.8 2.6 3.3-1.6.5-4.2 '
        '2.3-5.1 2.5-8.3.2-4.2-3-6.8-7-5.7Z"/>'
    ),
    "phone": (
        '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 '
        '19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 '
        '2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 '
        '16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 '
        '0 0 1 22 16.92Z"/>'
    ),
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
    "note": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/>'
        '<path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>'
    ),
    "alert": (
        '<path d="m10.29 3.86-8.1 14a2 2 0 0 0 1.74 3h16.15a2 2 0 0 0 1.74-3l-8.1-14'
        'a2 2 0 0 0-3.43 0Z"/><path d="M12 9v4M12 17h.01"/>'
    ),
}


def svg_icon(name: str, color: str = "#078f96", size: int = 24) -> QIcon:
    """Napravi oštru, skalabilnu linijsku ikonicu bez emoji fontova."""
    body = _ICON_PATHS[name]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(painter)
    painter.end()
    return QIcon(pixmap)


class Sidebar(QFrame):
    route_selected = Signal(str)

    ROUTES = [
        ("raspored", "Raspored", "calendar"),
        ("zahtjevi", "Novi zahtjevi", "bell"),
        ("pacijenti", "Pacijenti", "user"),
        ("izvjestaji", "Izvještaji", "chart"),
        ("postavke", "Postavke", "settings"),
    ]

    QUICK = [
        ("pacijenti", "Novi pacijent", "user-plus"),
        ("pacijenti", "Traži pacijenta", "search"),
        ("blockout", "Blokiraj vrijeme", "clock"),
        ("podsjetnici", "Podsjetnici", "bell"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(254)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 14)
        root_layout.setSpacing(0)
        navigation = QScrollArea()
        navigation.setObjectName("sidebarNavigation")
        navigation.setWidgetResizable(True)
        navigation.setFrameShape(QFrame.Shape.NoFrame)
        navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        navigation.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        navigation_body = QWidget()
        navigation_body.setObjectName("sidebarNavigationBody")
        layout = QVBoxLayout(navigation_body)
        layout.setContentsMargins(15, 24, 15, 8)
        layout.setSpacing(7)
        navigation.setWidget(navigation_body)
        root_layout.addWidget(navigation, 1)

        brand = QFrame()
        brand.setObjectName("sidebarBrand")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(12, 0, 4, 0)
        brand_layout.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("sidebarLogo")
        logo_path = paths.resource_path("web", "assets", "logo.png")
        logo_pixmap = QPixmap(str(logo_path)).scaled(
            52,
            52,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        logo.setPixmap(logo_pixmap)
        logo.setFixedSize(52, 52)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wordmark = QLabel(
            "<span style='font-size:20px; font-weight:700'>DENTALAND</span><br>"
            "<span style='font-size:9px; font-weight:600'>STOMATOLOŠKA ORDINACIJA</span>"
        )
        wordmark.setObjectName("sidebarWordmark")
        brand_layout.addWidget(logo)
        brand_layout.addWidget(wordmark, 1)
        layout.addWidget(brand)
        layout.addSpacing(24)

        self.buttons: dict[str, QPushButton] = {}
        self.pending_badge = QLabel()
        self.pending_badge.setObjectName("pendingBadge")
        self.pending_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pending_badge.hide()
        for route, text, icon in self.ROUTES:
            button = self._button(route, text, icon)
            self.buttons[route] = button
            if route == "zahtjevi":
                row = QFrame()
                row.setObjectName("pendingNavRow")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 10, 0)
                row_layout.setSpacing(0)
                row_layout.addWidget(button, 1)
                row_layout.addWidget(self.pending_badge)
                layout.addWidget(row)
            else:
                layout.addWidget(button)
        layout.addSpacing(24)
        quick_title = QLabel("Brzi pristup")
        quick_title.setObjectName("quickTitle")
        layout.addWidget(quick_title)
        for route, text, icon in self.QUICK:
            layout.addWidget(self._button(route, text, icon, quick=True))
        layout.addStretch()

        self.staff = QFrame()
        self.staff.setObjectName("sidebarStaff")
        staff_layout = QHBoxLayout(self.staff)
        staff_layout.setContentsMargins(10, 14, 8, 0)
        avatar = QLabel("OS")
        avatar.setObjectName("staffAvatar")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(39, 39)
        staff_text = QLabel("<b>Osoblje</b><br><span style='color:#31578a'>Administrator</span>")
        staff_layout.addWidget(avatar)
        staff_layout.addWidget(staff_text, 1)
        staff_layout.addWidget(QLabel("⌄"))
        root_layout.addWidget(self.staff)
        self._activate("raspored")

    def _button(self, route: str, text: str, icon: str, *, quick: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("nav", True)
        button.setProperty("quick", quick)
        button.setIcon(svg_icon(icon))
        button.setIconSize(QSize(24, 24))
        button.clicked.connect(lambda _checked=False, key=route: self._select(key))
        return button

    def _select(self, route: str) -> None:
        if route in self.buttons:
            self._activate(route)
        self.route_selected.emit(route)

    def _activate(self, route: str) -> None:
        for key, button in self.buttons.items():
            button.setProperty("active", key == route)
            button.style().unpolish(button)
            button.style().polish(button)

    def set_pending_count(self, count: int) -> None:
        self.pending_badge.setText(str(count))
        self.pending_badge.setVisible(count > 0)
