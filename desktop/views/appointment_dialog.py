"""Kompatibilnost (Faza B) — stari ``AppointmentDialog`` je sada unified editor.

Generički create workflow je zamijenjen ``AppointmentEditorDialog``-om u
``desktop/views/dialogs/``. Ovaj fajl ostaje samo da postojeći importi ne
puknu; novi kod treba da importuje iz ``desktop.views.dialogs``.
"""

from desktop.views.dialogs.appointment_editor import AppointmentEditorDialog

AppointmentDialog = AppointmentEditorDialog  # backward-compat alias

__all__ = ["AppointmentDialog", "AppointmentEditorDialog"]
