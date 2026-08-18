"""Ulazna tačka desktop aplikacije (Faza 0 GUI ljuska)."""

from __future__ import annotations

import sys
from datetime import date, timedelta

from PySide6.QtWidgets import QApplication

from dentaland.services import AppointmentService
from desktop.views.main_window import MainWindow


def current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def main() -> int:
    app = QApplication(sys.argv)
    service = AppointmentService.from_sqlite("dentaland.db")
    window = MainWindow(service)
    # Maksimizovan prozor koristi radnu površinu iznad Windows taskbara.
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
