"""Ulazna tačka desktop aplikacije (Faza 0 GUI ljuska)."""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtWidgets import QApplication

from dentaland import paths
from dentaland.services import AppointmentService
from desktop.views.main_window import MainWindow

ENV_REMOTE_DATABASE_URL = "DENTALAND_DATABASE_URL"


def current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _resolve_db_path() -> Path:
    """Put do baze za desktop run.

    Razvoj kroz ``scripts/dev_local.py`` pokreće desktop iz source tree
    root-a gdje ``dentaland.db`` već postoji (i dijeli se sa backendom) —
    tada se koristi taj fajl. Instalirana aplikacija (bez ``dentaland.db``
    u cwd-u) koristi user data folder kroz ``dentaland.paths``.
    """
    cwd_db = Path.cwd() / paths.DB_FILENAME
    if cwd_db.exists():
        return cwd_db
    return paths.database_path()


def main() -> int:
    app = QApplication(sys.argv)
    remote_url = os.environ.get(ENV_REMOTE_DATABASE_URL)
    if remote_url:
        # NAMJERNO odvojena putanja od podrazumijevane lokalne SQLite
        # upotrebe — Ljubina stvarna upotreba (bez ove env varijable)
        # ostaje potpuno nepromijenjena. Vidi CLAUDE.md/CURRENT_STATE.md
        # za kontekst: privremen most za testiranje protiv test VPS-a
        # preko SSH tunela, ne finalna Faza 1 arhitektura (ta ide preko
        # HTTP API-ja + RBAC, vidi desktop/remote_demo.py).
        service = AppointmentService.from_database_url(remote_url)
    else:
        db_path = _resolve_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        service = AppointmentService.from_sqlite(str(db_path))
    window = MainWindow(service)
    # Maksimizovan prozor koristi radnu površinu iznad Windows taskbara.
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
