"""Zajednički fixtures za GUI testove.

``QT_QPA_PLATFORM=offscreen`` se postavlja prije uvoza PySide6 da testovi
nikad ne otvore pravi prozor.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dentaland.services import AppointmentService  # noqa: E402
from desktop.fake_data import FakeStore  # noqa: E402


@pytest.fixture()
def week_start() -> date:
    return date(2026, 8, 17)  # ponedjeljak


@pytest.fixture()
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture()
def appointment_service(tmp_path) -> AppointmentService:
    """Servis nad SQLite bazom sa seed-ovanim doktorima (Ljubo/Zorka/Ana)."""
    return AppointmentService.from_sqlite(str(tmp_path / "dentaland.db"))
