"""Globalni QSS i paleta boja desktop aplikacije.

Jedno mjesto za vizuelni identitet — ``MainWindow`` poziva ``apply_theme``
umjesto da drži ~190 linija QSS-a u vlastitom workflow kodu. QSS je
module-level konstanta ``GLOBAL_STYLESHEET`` (čista, bez Qt instanci), a
``apply_theme`` ga primjenjuje na dati prozor i postavlja paletu na
``QApplication``.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

GLOBAL_STYLESHEET = """
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
#schedulePage { background-color: #ffffff; }
#topHeader { border-bottom: 1px solid #e1e9ef; }
#pageTitle { font-size: 19px; font-weight: 700; }
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
    min-width: 116px;
    min-height: 38px;
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
    background-color: #f7fbfc;
    border: 1px solid #cfe0e6;
    border-radius: 9px;
    font-size: 13px;
    font-weight: 600;
    padding: 0 10px;
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
#doctorLegend {
    background-color: #ffffff;
    border: 1px solid #d9e3ea;
    border-radius: 10px;
}
#doctorLegendTitle { font-size: 14px; font-weight: 700; }
#doctorLegendRow { background-color: #ffffff; }
#doctorLegendName { font-size: 13px; font-weight: 700; }
#doctorLegendMeta { color: #31578a; font-size: 11px; }
#dashboardPanels, #dashboardPanelContent { background-color: #ffffff; }
#dashboardSectionTitle {
    font-size: 13px;
    font-weight: 700;
    padding: 4px 2px 1px 2px;
}
#dashboardBox {
    font-size: 12px;
    border-radius: 9px;
    margin-top: 14px;
    padding-top: 12px;
}
#dashboardBox[tone="info"] {
    background-color: #f0fafb;
    border-color: #bfe5e8;
}
#dashboardBox[tone="warning"] {
    background-color: #fff9ed;
    border-color: #f2d99d;
}
#dashboardBox[tone="danger"] {
    background-color: #fff2f4;
    border-color: #f3c4cd;
}
#dashboardBox[tone="info"] QLabel { background-color: #f0fafb; }
#dashboardBox[tone="warning"] QLabel { background-color: #fff9ed; }
#dashboardBox[tone="danger"] QLabel { background-color: #fff2f4; }
#dashboardBox QLabel { font-size: 11px; font-weight: 400; }
#dashboardCardHeader { background-color: transparent; }
#dashboardCardIcon { background-color: transparent; }
#dashboardCardTitle {
    background-color: transparent;
    color: #10213d;
    font-size: 12px;
    font-weight: 700;
}
#dashboardCardCount {
    background-color: transparent;
    min-width: 25px;
    font-size: 20px;
    font-weight: 700;
}
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


def apply_theme(window: QWidget) -> None:
    """Primijeni globalnu paletu i QSS na dat prozor (root window)."""
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
    window.setStyleSheet(GLOBAL_STYLESHEET)
