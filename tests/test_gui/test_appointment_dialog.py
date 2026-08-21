"""Testovi unified editora za Novi/Uredi termin (Faza B)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from PySide6.QtWidgets import QDialog

from desktop.views.dialogs.appointment_editor import AppointmentEditorDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")
START = datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO)

DOCTORS = [(1, "Ljubo"), (2, "Zorka")]
SERVICES = [("Kontrola", 30), ("Plomba", 60)]


def _make_dialog(
    qtbot,
    *,
    appointment=None,
    selected_doctor_id: int | None = None,
) -> AppointmentEditorDialog:
    dlg = AppointmentEditorDialog(
        DOCTORS,
        SERVICES,
        START,
        appointment=appointment,
        selected_doctor_id=selected_doctor_id,
    )
    qtbot.addWidget(dlg)
    return dlg


def test_editor_ima_sva_polja(qtbot) -> None:
    dlg = _make_dialog(qtbot)
    assert dlg.name_edit is not None
    assert dlg.phone_edit is not None
    assert dlg.email_edit is not None
    assert dlg.doctor_combo.count() == 1 + len(DOCTORS)  # placeholder + doktori
    assert dlg.date_edit is not None
    assert dlg.time_edit is not None
    assert dlg.duration_edit is not None
    assert dlg.service_combo.count() == 2
    assert dlg.note_edit is not None


def test_trajanje_se_predlaze_iz_usluge(qtbot) -> None:
    dlg = _make_dialog(qtbot)
    assert dlg.duration_edit.value() == 30  # prva usluga "Kontrola"
    dlg.service_combo.setCurrentIndex(1)  # "Plomba"
    assert dlg.duration_edit.value() == 60


def test_create_prefill_start(qtbot) -> None:
    dlg = _make_dialog(qtbot)
    assert dlg.get_data()["start"] == START


def test_doctor_preselection(qtbot) -> None:
    dlg = _make_dialog(qtbot, selected_doctor_id=2)
    assert dlg.selected_doctor_id() == 2


def test_bez_preselectiona_doktor_nije_izabran(qtbot) -> None:
    dlg = _make_dialog(qtbot)
    assert dlg.selected_doctor_id() is None


def test_edit_prefill(qtbot) -> None:
    appt = SimpleNamespace(
        id=1,
        patient_name="Ana Anić",
        phone="061/123",
        email="ana@x.com",
        service="Plomba",
        note="napomena",
        start=datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO),
        end=datetime(2026, 8, 17, 11, 0, tzinfo=SARAJEVO),
        doctor_id=2,
    )
    dlg = _make_dialog(qtbot, appointment=appt)
    assert dlg.name_edit.text() == "Ana Anić"
    assert dlg.phone_edit.text() == "061/123"
    assert dlg.email_edit.text() == "ana@x.com"
    assert dlg.note_edit.toPlainText() == "napomena"
    assert dlg.selected_doctor_id() == 2
    assert dlg.service_combo.currentText() == "Plomba"
    assert dlg.duration_edit.value() == 60  # end - start
    assert dlg.get_data()["start"] == datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO)


def test_edit_mode_cuva_rucno_trajanje(qtbot) -> None:
    appt = SimpleNamespace(
        id=1,
        patient_name="Ana Anić",
        phone="",
        email="",
        service="Plomba",  # default 60
        note="",
        start=datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO),
        end=datetime(2026, 8, 17, 11, 30, tzinfo=SARAJEVO),  # stvarno 90 min
        doctor_id=1,
    )
    dlg = _make_dialog(qtbot, appointment=appt)
    assert dlg.duration_edit.value() == 90


def test_edit_mode_promjena_usluge_azurira_trajanje(qtbot) -> None:
    services = [("Kontrola", 30), ("Izbjeljivanje", 45), ("Plomba", 60)]
    appt = SimpleNamespace(
        id=1,
        patient_name="Ana Anić",
        phone="",
        email="",
        service="Plomba",
        note="",
        start=datetime(2026, 8, 17, 10, 0, tzinfo=SARAJEVO),
        end=datetime(2026, 8, 17, 11, 30, tzinfo=SARAJEVO),  # 90 min
        doctor_id=1,
    )
    dlg = AppointmentEditorDialog(DOCTORS, services, START, appointment=appt)
    qtbot.addWidget(dlg)
    assert dlg.duration_edit.value() == 90  # prefill zadržan
    dlg.service_combo.setCurrentIndex(1)  # "Izbjeljivanje" default 45
    assert dlg.duration_edit.value() == 45


def test_get_data_vraca_doktora_i_trajanje(qtbot) -> None:
    dlg = _make_dialog(qtbot, selected_doctor_id=1)
    dlg.name_edit.setText("Ana")
    dlg.duration_edit.setValue(45)
    data = dlg.get_data()
    assert data["doctor_id"] == 1
    assert data["duration_min"] == 45
    assert data["service"] == "Kontrola"


def test_validacija_zahteva_ime(qtbot) -> None:
    dlg = _make_dialog(qtbot, selected_doctor_id=1)
    dlg.name_edit.setText("")
    assert dlg.validate() == "Unesite ime pacijenta."


def test_validacija_zahteva_doktora(qtbot) -> None:
    dlg = _make_dialog(qtbot)  # bez preselectiona → placeholder
    dlg.name_edit.setText("Ana")
    assert dlg.validate() == "Izaberite doktora."


def test_accept_sa_nevalidnim_unosom_ne_zatvara(qtbot) -> None:
    dlg = _make_dialog(qtbot)
    dlg.name_edit.setText("")  # nevalidno
    dlg.accept()
    assert dlg.result() != QDialog.DialogCode.Accepted
    assert dlg._error_label.text() == "Unesite ime pacijenta."


def test_napomena_je_slobodan_tekst(qtbot) -> None:
    dlg = _make_dialog(qtbot, selected_doctor_id=1)
    tekst = "Bilo šta! 123 —\nnovi red 😀"
    dlg.note_edit.setPlainText(tekst)
    assert dlg.get_data()["note"] == tekst
