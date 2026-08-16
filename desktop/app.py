"""Ulazna tačka desktop aplikacije (Faza 0 GUI ljuska)."""

from __future__ import annotations

import sys
from datetime import date, timedelta

from PySide6.QtWidgets import QApplication

from desktop.fake_data import FakeStore
from desktop.views.main_window import MainWindow


def current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def main() -> int:
    app = QApplication(sys.argv)
    store = FakeStore.seeded(current_week_start())
    window = MainWindow(store)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
