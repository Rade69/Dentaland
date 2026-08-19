"""Reusable vizuelna osnova za modalne dijaloge (Faza B redizajna).

Zamjenjuje generički ``QDialogButtonBox`` OK/Cancel izgled zajedničkim
Dentaland stilom: white surface, dark navy text, teal primary, zaobljeni
uglovi, blag border. Struktura: header (naslov) → body (sadržaj) → inline
error → footer (akcije).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class BaseDialog(QDialog):
    """Zajednička osnova za glavne modalne tokove — bez emoji, bez generičkog OK/Cancel."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setObjectName("baseDialog")
        self.setMinimumWidth(430)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("dialogTitle")

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(12)

        self._error_label = QLabel()
        self._error_label.setObjectName("dialogError")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)

        self._footer = QHBoxLayout()
        self._footer.setContentsMargins(0, 0, 0, 0)
        self._footer.setSpacing(8)
        self._footer.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)
        root.addWidget(self._title_label)
        root.addLayout(self._body)
        root.addWidget(self._error_label)
        root.addLayout(self._footer)

        self._apply_style()

    def body_layout(self) -> QVBoxLayout:
        """Mjesto gdje podklasa dodaje sadržaj forme."""
        return self._body

    def add_primary_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("dialogPrimaryButton")
        button.clicked.connect(self.accept)
        self._footer.addWidget(button)
        return button

    def add_secondary_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("dialogSecondaryButton")
        button.clicked.connect(self.reject)
        self._footer.addWidget(button)
        return button

    def make_icon_label(
        self, icon_name: str, color: str = "#078f96", size: int = 16
    ) -> QLabel:
        """Mala ikonica u krugu — za redove sa ikonicom (Detalji)."""
        from desktop.views.sidebar import svg_icon

        label = QLabel()
        label.setPixmap(svg_icon(icon_name, color, size).pixmap(size, size))
        label.setFixedSize(size + 12, size + 12)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"background-color: #eef8f9; border-radius: {(size + 12) // 2}px;"
        )
        return label

    def add_outline_button(self, text: str, kind: str = "teal") -> QPushButton:
        """Dugme sa obojenim obrisom — ``teal`` za edit/move, ``danger`` za cancel."""
        button = QPushButton(text)
        button.setObjectName("outlineTealButton" if kind == "teal" else "outlineDangerButton")
        self.body_layout().addWidget(button)
        return button

    def show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setVisible(True)

    def clear_error(self) -> None:
        self._error_label.setText("")
        self._error_label.setVisible(False)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #baseDialog {
                background-color: #ffffff;
                border: 1px solid #d9e3ea;
                border-radius: 12px;
            }
            #dialogTitle {
                color: #10213d;
                font-size: 16px;
                font-weight: 700;
            }
            #dialogError {
                color: #c0392b;
                background-color: #fdecea;
                border: 1px solid #f5c6cb;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QDateEdit, QTimeEdit, QSpinBox, QPlainTextEdit {
                background-color: #ffffff;
                color: #10213d;
                border: 1px solid #cad8e2;
                border-radius: 6px;
                min-height: 32px;
                padding: 2px 8px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus,
            QSpinBox:focus, QPlainTextEdit:focus { border-color: #078f96; }
            #dialogPrimaryButton {
                background-color: #078f96;
                color: #ffffff;
                border: 1px solid #078f96;
                border-radius: 6px;
                min-height: 36px;
                padding: 2px 18px;
                font-weight: 600;
            }
            #dialogPrimaryButton:hover { background-color: #06777d; }
            #dialogSecondaryButton {
                background-color: #ffffff;
                color: #10213d;
                border: 1px solid #cad8e2;
                border-radius: 6px;
                min-height: 36px;
                padding: 2px 18px;
            }
            #dialogSecondaryButton:hover { background-color: #eef8f9; }
            #outlineTealButton {
                background-color: #ffffff; color: #078f96;
                border: 1px solid #078f96; border-radius: 6px;
                min-height: 34px; padding: 2px 12px; font-weight: 600;
            }
            #outlineTealButton:hover { background-color: #eef8f9; }
            #outlineDangerButton {
                background-color: #ffffff; color: #ef334f;
                border: 1px solid #ef334f; border-radius: 6px;
                min-height: 34px; padding: 2px 12px; font-weight: 600;
            }
            #outlineDangerButton:hover { background-color: #fdecef; }
            #editorFieldLabel { color: #42526b; font-weight: 600; font-size: 12px; }
            """
        )
