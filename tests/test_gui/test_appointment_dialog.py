"""Testovi dijaloga za unos termina."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from PySide6.QtCore import QDate, QDateTime, QTime

from desktop.views.appointment_dialog import AppointmentDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")
DEFAULT_START = datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO)


@pytest.fixture()
def dialog(qtbot) -> AppointmentDialog:
    dlg = AppointmentDialog(["Kontrola", "Plomba"], DEFAULT_START)
    qtbot.addWidget(dlg)
    return dlg


def test_dijalog_ima_sva_polja(dialog: AppointmentDialog) -> None:
    assert dialog.name_edit is not None
    assert dialog.phone_edit is not None
    assert dialog.email_edit is not None
    assert dialog.service_combo.count() == 2
    assert dialog.start_edit is not None
    assert dialog.note_edit is not None


def test_napomena_je_slobodan_tekst(dialog: AppointmentDialog) -> None:
    tekst = "Bilo šta! 123 —\nnovi red, simboli @#€ 😀"
    dialog.note_edit.setPlainText(tekst)
    assert dialog.get_data()["note"] == tekst


def test_start_je_predpopunjen_predloženim_vremenom(dialog: AppointmentDialog) -> None:
    assert dialog.get_data()["start"] == DEFAULT_START


def test_start_se_moze_slobodno_izmijeniti_na_bilo_koji_minut(
    dialog: AppointmentDialog,
) -> None:
    """Klik u mreži je samo predlog — osoblje može upisati bilo koji tačan minut."""
    dialog.start_edit.setDateTime(QDateTime(QDate(2026, 8, 17), QTime(14, 17)))
    assert dialog.get_data()["start"] == datetime(2026, 8, 17, 14, 17, tzinfo=SARAJEVO)


def test_get_data_vraca_unete_podatke(dialog: AppointmentDialog) -> None:
    dialog.name_edit.setText("Ana Anić")
    dialog.phone_edit.setText("061/123-456")
    dialog.email_edit.setText("ana@example.com")
    dialog.service_combo.setCurrentIndex(1)
    dialog.note_edit.setPlainText("Bez napomene")

    assert dialog.get_data() == {
        "patient_name": "Ana Anić",
        "phone": "061/123-456",
        "email": "ana@example.com",
        "service": "Plomba",
        "note": "Bez napomene",
        "start": DEFAULT_START,
    }
