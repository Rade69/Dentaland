"""Jednostavne placeholder stranice za funkcionalnosti van DENT-009 obima."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class StubPage(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        heading = QLabel(title)
        heading.setObjectName("stubTitle")
        message = QLabel("Uskoro")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(heading)
        layout.addWidget(message, 1)
