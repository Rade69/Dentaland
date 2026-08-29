"""Controller za appointment workflow (REF-04).

Izvučen iz ``MainWindow``: otvara dijaloge, pretvara UI unos u service pozive
(facade), mapira očekivane greške u user-facing feedback i poziva refresh
callback nakon uspješne mutacije.

Pravila sloja (plan sekcija 3.2): Controller SMIJE uvoziti PySide6 i pozivati
Dialog klase kao crnu kutiju, ali NE smije crtati widgete niti raditi SQL —
sav pristup podacima ide kroz ``store`` (facade).

Dijalog klase se dohvataju lazy importom iz ``desktop.views.dialogs`` u
trenutku poziva (late binding), umjesto module-level importa: GUI testovi
monkeypatch-uju dijaloge na ``desktop.views.dialogs`` modulu i neki to rade
i NAKON konstrukcije ``MainWindow``-a. Ovo kida cirkularni import
``main_window`` ↔ ``appointment_controller`` (REF-16).
"""

from __future__ import annotations

import weakref
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from dentaland.services import OverlapError

DEFAULT_MANUAL_DURATION_MINUTES = 60


class AppointmentController:
    """Appointment CRUD workflow, nezavisan od ``MainWindow`` konkretne klase."""

    def __init__(
        self,
        store: Any,
        parent_widget: QWidget,
        refresh_callback: Callable[[], None],
        *,
        doctors_provider: Callable[[], list] = lambda: [],
        has_doctors_provider: Callable[[], bool] = lambda: False,
        current_doctor_id_provider: Callable[[], int | None] = lambda: None,
    ) -> None:
        self._store = store
        self._parent_widget_ref: Any
        try:
            self._parent_widget_ref = weakref.ref(parent_widget)
        except TypeError:
            # parent nije weakref-able (npr. SimpleNamespace u testovima) —
            # čuvaj jaku referencu kroz closure (nema ciklusa za QWidget).
            self._parent_widget_ref = lambda: parent_widget
        self._refresh_callback = refresh_callback
        self._doctors_provider = doctors_provider
        self._has_doctors_provider = has_doctors_provider
        self._current_doctor_id_provider = current_doctor_id_provider

    @property
    def _parent_widget(self) -> QWidget | None:
        """Parent widget kroz weak referencu — sprječava reference ciklus (REF-10)."""
        return self._parent_widget_ref()

    # --- UI kontekst (doctor state kroz eksplicitne provider-e) ---

    def _doctors(self) -> list:
        return self._doctors_provider()

    def _has_doctors(self) -> bool:
        return self._has_doctors_provider()

    def _current_doctor_id(self) -> int | None:
        return self._current_doctor_id_provider()

    def service_options(self) -> list[tuple[str, int]]:
        """Usluge kao ``(naziv, trajanje_min)`` — iz store-a, sa legacy fallback-om."""
        fn = getattr(self._store, "service_options", None)
        if callable(fn):
            return [(o.naziv, o.trajanje_min) for o in fn()]
        services = getattr(self._store, "services", None)
        if callable(services):
            return [(name, DEFAULT_MANUAL_DURATION_MINUTES) for name in services()]
        return []

    # --- workflow ---

    def on_slot_selected(self, start: datetime) -> None:
        from desktop.views.dialogs import AppointmentEditorDialog

        dialog = AppointmentEditorDialog(
            [(d.id, d.ime) for d in self._doctors()],
            self.service_options(),
            start,
            selected_doctor_id=self._current_doctor_id(),
            parent=self._parent_widget,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            data = dialog.get_data()
            doctor_id = data["doctor_id"]
            if self._has_doctors() and doctor_id is None:
                dialog.show_error("Izaberite doktora.")
                continue
            end = data["start"] + timedelta(minutes=data["duration_min"])
            if doctor_id is not None and hasattr(self._store, "set_doctor"):
                self._store.set_doctor(doctor_id)
            try:
                self._store.create(
                    patient_name=data["patient_name"],
                    phone=data["phone"],
                    email=data["email"],
                    service=data["service"],
                    note=data["note"],
                    start=data["start"],
                    end=end,
                )
                break
            except OverlapError as exc:
                dialog.show_error(str(exc))
        self._refresh_callback()

    def edit_appointment(self, appt: Any) -> None:
        from desktop.views.dialogs import AppointmentEditorDialog

        dialog = AppointmentEditorDialog(
            [(d.id, d.ime) for d in self._doctors()],
            self.service_options(),
            appt.start,
            appointment=appt,
            parent=self._parent_widget,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            data = dialog.get_data()
            doctor_id = data["doctor_id"]
            if self._has_doctors() and doctor_id is None:
                dialog.show_error("Izaberite doktora.")
                continue
            end = data["start"] + timedelta(minutes=data["duration_min"])
            update_fn = getattr(self._store, "update", None)
            if not callable(update_fn):
                dialog.show_error("Uređivanje nije podržano za ovaj izvor podataka.")
                continue
            try:
                update_fn(
                    appt.id,
                    patient_name=data["patient_name"],
                    phone=data["phone"],
                    email=data["email"],
                    doctor_id=doctor_id,
                    service=data["service"],
                    note=data["note"],
                    start=data["start"],
                    end=end,
                )
                break
            except OverlapError as exc:
                dialog.show_error(str(exc))
        self._refresh_callback()

    def open_appointment_details(self, appt_id: int) -> None:
        from desktop.views.dialogs import AppointmentDetailsDialog

        appt = self._store.get(appt_id)
        if appt is None:
            return
        dialog = AppointmentDetailsDialog(appt, self._parent_widget)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            action = dialog.selected_action()
            if action is not None:
                self.handle_appointment_action(appt_id, action)

    def handle_appointment_action(self, appt_id: int, action: str) -> None:
        if action == "open_details":
            self.open_appointment_details(appt_id)
            return
        if action == "edit":
            appt = self._store.get(appt_id)
            if appt is not None:
                self.edit_appointment(appt)
            return
        if action == "move":
            appt = self._store.get(appt_id)
            if appt is not None:
                self.move_appointment(appt)
            return
        if action == "cancel":
            appt = self._store.get(appt_id)
            if appt is not None:
                self.cancel_appointment(appt)
            return
        if action == "delete":
            appt = self._store.get(appt_id)
            if appt is not None:
                self.delete_appointment(appt)
            return
        method_map = {
            "confirm": "mark_confirmed",
            "reject": "cancel",
            "arrived": "mark_arrived",
            "unarrived": "unmark_arrived",
            "completed": "mark_completed",
            "no_show": "mark_no_show",
        }
        method_name = method_map.get(action)
        if method_name is None:
            return
        method = getattr(self._store, method_name, None)
        if callable(method):
            try:
                method(appt_id)
            except ValueError as exc:
                QMessageBox.warning(self._parent_widget, "Akcija nije uspjela", str(exc))
        self._refresh_callback()

    def move_appointment(self, appt: Any) -> None:
        from desktop.views.dialogs import MoveAppointmentDialog

        dialog = MoveAppointmentDialog(appt, self._parent_widget)
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            new_start, duration_min = dialog.get_data()
            new_end = new_start + timedelta(minutes=duration_min)
            try:
                self._store.move(appt.id, new_start, new_end)
                break
            except OverlapError as exc:
                dialog.show_error(str(exc))
        self._refresh_callback()

    def move_appointment_slot(self, appt_id: int, new_start: datetime, new_end: datetime) -> bool:
        """Bezdijaloški move za drag&drop — na OverlapError tiho vraća False."""
        try:
            self._store.move(appt_id, new_start, new_end)
        except OverlapError:
            return False
        return True

    def cancel_appointment(self, appt: Any) -> None:
        from desktop.views.dialogs import CancelAppointmentDialog

        dialog = CancelAppointmentDialog(appt, self._parent_widget)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cancel_fn = getattr(self._store, "cancel", None)
            if callable(cancel_fn):
                try:
                    cancel_fn(appt.id)
                except ValueError as exc:
                    QMessageBox.warning(
                        self._parent_widget, "Otkazivanje nije uspjelo", str(exc)
                    )
            self._refresh_callback()

    def delete_appointment(self, appt: Any) -> None:
        from desktop.views.dialogs import DeleteAppointmentDialog

        dialog = DeleteAppointmentDialog(appt, self._parent_widget)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            delete_fn = getattr(self._store, "delete", None)
            if callable(delete_fn):
                try:
                    delete_fn(appt.id)
                except ValueError as exc:
                    QMessageBox.warning(
                        self._parent_widget, "Brisanje nije uspjelo", str(exc)
                    )
            self._refresh_callback()
