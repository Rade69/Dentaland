"""Testovi pomjeranja i otkazivanja termina (Faza C — move/cancel modal)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from PySide6.QtWidgets import QLabel, QPushButton

from desktop.views.dialogs.cancel_appointment import CancelAppointmentDialog
from desktop.views.dialogs.delete_appointment import DeleteAppointmentDialog
from desktop.views.dialogs.move_appointment import MoveAppointmentDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")


def _appt() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        patient_name="Radovan Stojanović",
        phone="061",
        email="r@x.com",
        service="Kontrola",
        note="",
        start=datetime(2026, 8, 19, 9, 0, tzinfo=SARAJEVO),
        end=datetime(2026, 8, 19, 10, 30, tzinfo=SARAJEVO),
        doctor_name="Ljubo",
        status=SimpleNamespace(value="SCHEDULED"),
        confirmed_at=None,
        arrived_at=None,
    )


def test_move_dialog_predlaze_trenutno_vrijeme_i_trajanje(qtbot) -> None:
    dialog = MoveAppointmentDialog(_appt())
    qtbot.addWidget(dialog)
    start, duration = dialog.get_data()
    assert start == datetime(2026, 8, 19, 9, 0, tzinfo=SARAJEVO)
    assert duration == 90  # 09:00–10:30 = 90 min


def test_move_dialog_cuva_trajanje(qtbot) -> None:
    dialog = MoveAppointmentDialog(_appt())
    qtbot.addWidget(dialog)
    assert dialog.duration_edit.value() == 90
    dialog.duration_edit.setValue(60)
    _start, duration = dialog.get_data()
    assert duration == 60


def test_cancel_dialog_prikazuje_pacijenta_i_napomenu_istorije(qtbot) -> None:
    dialog = CancelAppointmentDialog(_appt())
    qtbot.addWidget(dialog)
    patient = dialog.findChild(QLabel, "cancelPatient")
    note = dialog.findChild(QLabel, "cancelNote")
    assert patient is not None and patient.text() == "Radovan Stojanović"
    assert note is not None and note.text() == "Otkazani termin ostaje sačuvan u istoriji."


def test_delete_dialog_prikazuje_pacijenta_i_upozorenje(qtbot) -> None:
    dialog = DeleteAppointmentDialog(_appt())
    qtbot.addWidget(dialog)
    patient = dialog.findChild(QLabel, "deletePatient")
    note = dialog.findChild(QLabel, "deleteNote")
    assert patient is not None and patient.text() == "Radovan Stojanović"
    assert note is not None and 'Otkaži termin' in note.text()


def test_delete_dugme_ne_reaguje_na_enter(qtbot) -> None:
    """Kritičan zahtjev iz plana (F.4): Enter ne smije aktivirati brisanje."""
    dialog = DeleteAppointmentDialog(_appt())
    qtbot.addWidget(dialog)
    delete_button = next(
        b for b in dialog.findChildren(QPushButton) if b.text() == "Izbriši termin"
    )
    assert delete_button.autoDefault() is False
    assert delete_button.isDefault() is False


def test_delete_dialog_accept_selektuje_ispravnu_akciju(qtbot) -> None:
    dialog = DeleteAppointmentDialog(_appt())
    qtbot.addWidget(dialog)
    delete_button = next(
        b for b in dialog.findChildren(QPushButton) if b.text() == "Izbriši termin"
    )
    delete_button.click()
    assert dialog.result() != 0  # QDialog.Rejected == 0; accept() je pozvan
