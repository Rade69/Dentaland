"""Modalni dijalozi desktop aplikacije (Faze B i C redizajna)."""

from desktop.views.dialogs.appointment_details import AppointmentDetailsDialog
from desktop.views.dialogs.appointment_editor import AppointmentEditorDialog
from desktop.views.dialogs.base_dialog import BaseDialog
from desktop.views.dialogs.cancel_appointment import CancelAppointmentDialog
from desktop.views.dialogs.move_appointment import MoveAppointmentDialog

__all__ = [
    "AppointmentDetailsDialog",
    "AppointmentEditorDialog",
    "BaseDialog",
    "CancelAppointmentDialog",
    "MoveAppointmentDialog",
]
