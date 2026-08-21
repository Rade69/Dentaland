"""Testovi Detalji termina dijaloga (Faza C)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from PySide6.QtWidgets import QComboBox

from desktop.views.dialogs.appointment_details import AppointmentDetailsDialog

SARAJEVO = ZoneInfo("Europe/Sarajevo")


def _appt(status: str = "SCHEDULED", confirmed_at=None, arrived_at=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        patient_name="Ana Anić",
        phone="061/111-222",
        email="ana@example.com",
        service="Kontrola",
        note="",
        start=datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        end=datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
        doctor_name="Ljubo",
        status=SimpleNamespace(value=status),
        confirmed_at=confirmed_at,
        arrived_at=arrived_at,
    )


def _action_labels(dialog: AppointmentDetailsDialog) -> list[str]:
    return [b.text() for b in dialog._action_buttons]


def test_detalji_prikazuju_status_badge(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt())
    qtbot.addWidget(dialog)
    assert "Čeka potvrdu" in dialog.status_badge.text()


def test_detalji_nemaju_status_dropdown(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt())
    qtbot.addWidget(dialog)
    assert dialog.findChildren(QComboBox) == []


def test_akcije_za_cekaju_potvrdu(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt())  # SCHEDULED, bez confirmed/arrived
    qtbot.addWidget(dialog)
    labels = _action_labels(dialog)
    assert "Potvrdi termin" in labels
    assert "Pacijent je stigao" in labels
    assert "Označi kao završen" in labels
    assert "Označi 'nije došao'" in labels
    assert "Uredi termin" in labels
    assert "Pomjeri termin" in labels
    assert "Otkaži termin" in labels


def test_potvrdjen_termin_nema_potvrdi_akciju(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt(confirmed_at=object()))
    qtbot.addWidget(dialog)
    labels = _action_labels(dialog)
    assert "Potvrdi termin" not in labels
    assert "Pacijent je stigao" in labels


def test_terminalni_termin_nema_povratnih_akcija(qtbot) -> None:
    """Terminalni termin nema STATUSNE akcije (confirm/arrived/completed/...),
    ali "Izbriši termin" (Faza F) je namjerno dostupan za sve statuse — vidi
    test_izbrisi_termin_dostupan_za_terminalni_status niže."""
    dialog = AppointmentDetailsDialog(_appt(status="COMPLETED"))
    qtbot.addWidget(dialog)
    assert _action_labels(dialog) == ["Izbriši termin"]
    assert "Završen" in dialog.status_badge.text()


def test_izbrisi_termin_dostupan_za_aktivan_i_terminalni_status(qtbot) -> None:
    active = AppointmentDetailsDialog(_appt())
    qtbot.addWidget(active)
    assert "Izbriši termin" in _action_labels(active)

    terminal = AppointmentDetailsDialog(_appt(status="CANCELLED"))
    qtbot.addWidget(terminal)
    assert "Izbriši termin" in _action_labels(terminal)


def test_izbrisi_termin_selektuje_delete_akciju(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt())
    qtbot.addWidget(dialog)
    delete_button = next(b for b in dialog._action_buttons if b.text() == "Izbriši termin")
    delete_button.click()
    assert dialog.selected_action() == "delete"


def test_selected_action_nakon_klika(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt())
    qtbot.addWidget(dialog)
    confirm = next(b for b in dialog._action_buttons if b.text() == "Potvrdi termin")
    confirm.click()
    assert dialog.selected_action() == "confirm"


def test_operativne_akcije_vracaju_svoje_kodove(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt())
    qtbot.addWidget(dialog)
    buttons = {b.text(): b for b in dialog._action_buttons}
    buttons["Uredi termin"].click()
    assert dialog.selected_action() == "edit"

    dialog2 = AppointmentDetailsDialog(_appt())
    qtbot.addWidget(dialog2)
    buttons2 = {b.text(): b for b in dialog2._action_buttons}
    buttons2["Otkaži termin"].click()
    assert dialog2.selected_action() == "cancel"


def test_no_show_prikazuje_odvojenu_labelu(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt(status="NO_SHOW"))
    qtbot.addWidget(dialog)
    assert "Nije došao" in dialog.status_badge.text()
    assert "Otkazan" not in dialog.status_badge.text()


def test_cancelled_prikazuje_otkazan(qtbot) -> None:
    dialog = AppointmentDetailsDialog(_appt(status="CANCELLED"))
    qtbot.addWidget(dialog)
    assert "Otkazan" in dialog.status_badge.text()
    assert "Nije došao" not in dialog.status_badge.text()
