"""Testovi pomjeranja i otkazivanja termina (Faza C — move/cancel modal)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from PySide6.QtWidgets import QLabel

from desktop.views.dialogs.cancel_appointment import CancelAppointmentDialog
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
