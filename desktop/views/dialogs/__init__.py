"""Modalni dijalozi desktop aplikacije (Faze B i C redizajna)."""

from desktop.views.dialogs.appointment_details import AppointmentDetailsDialog
from desktop.views.dialogs.appointment_editor import AppointmentEditorDialog
from desktop.views.dialogs.base_dialog import BaseDialog
from desktop.views.dialogs.blockout_delete_confirm import BlockoutDeleteConfirmDialog
from desktop.views.dialogs.cancel_appointment import CancelAppointmentDialog
from desktop.views.dialogs.delete_appointment import DeleteAppointmentDialog
from desktop.views.dialogs.move_appointment import MoveAppointmentDialog
from desktop.views.dialogs.process_request import ProcessRequestDialog

__all__ = [
    "AppointmentDetailsDialog",
    "AppointmentEditorDialog",
    "BaseDialog",
    "BlockoutDeleteConfirmDialog",
    "CancelAppointmentDialog",
    "DeleteAppointmentDialog",
    "MoveAppointmentDialog",
    "ProcessRequestDialog",
]
