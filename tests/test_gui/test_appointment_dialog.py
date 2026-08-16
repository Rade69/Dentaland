"""Testovi dijaloga za unos termina."""

from __future__ import annotations

import pytest

from desktop.views.appointment_dialog import AppointmentDialog


@pytest.fixture()
def dialog(qtbot) -> AppointmentDialog:
    dlg = AppointmentDialog(["Kontrola", "Plomba"])
    qtbot.addWidget(dlg)
    return dlg


def test_dijalog_ima_sva_polja(dialog: AppointmentDialog) -> None:
    assert dialog.name_edit is not None
    assert dialog.phone_edit is not None
    assert dialog.email_edit is not None
    assert dialog.service_combo.count() == 2
    assert dialog.note_edit is not None


def test_napomena_je_slobodan_tekst(dialog: AppointmentDialog) -> None:
    tekst = "Bilo šta! 123 —\nnovi red, simboli @#€ 😀"
    dialog.note_edit.setPlainText(tekst)
    assert dialog.get_data()["note"] == tekst


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
    }
