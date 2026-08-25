"""Controller za obradu pending zahtjeva (REF-07).

Premješten iz ``desktop/views/requests_panel.py`` — isti dialog/business tok,
sada u Controller sloju. ``RequestController`` je stateless (samo drži
``store``), pa ga View može instancirati ili primiti kroz DI.

Napomena: ``OverlapError`` je od REF-01 kanonizovana JEDNA klasa u
``availability.py`` (re-eksport iz ``dentaland.services``) — više ne postoji
odvojeni ``requests.OverlapError`` vs ``booking.OverlapError``.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from dentaland.services import OverlapError
from desktop.views.dialogs.process_request import ProcessRequestDialog


class RequestController:
    """Obrada jednog pending zahtjeva kroz ProcessRequestDialog."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def process_pending_request(self, request: Any, parent: QWidget) -> bool | None:
        """Obradi pending zahtjev kroz jedini zajednički dialog/business tok.

        Vraća ``True`` kad je zahtjev potvrđen ili odbijen, ``False`` kada je
        dijalog zatvoren bez akcije, a ``None`` kada nema doktora/usluga.
        """
        doctors_method = getattr(self._store, "doctors", None)
        services_method = getattr(self._store, "service_choices", None)
        doctors = [(d.id, d.ime) for d in doctors_method()] if callable(doctors_method) else []
        services = list(services_method()) if callable(services_method) else []
        if not doctors or not services:
            return None

        dialog = ProcessRequestDialog(request, doctors, services, parent)
        while True:
            dialog.exec()
            action = dialog.selected_action()
            if action == "confirm":
                doctor_id, service_id, start = dialog.values()
                try:
                    self._store.confirm_pending(request.id, doctor_id, service_id, start)
                except (OverlapError, ValueError) as exc:
                    dialog.show_error(str(exc))
                    continue
                return True
            if action == "reject":
                self._store.reject_pending(request.id)
                return True
            return False
