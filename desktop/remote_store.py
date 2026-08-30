""""Store" adapter za daljinski demo (DENT-IMPROVE-020).

Implementira TAČNO metode koje ``desktop/views/requests_panel.py``
(``DashboardPanels``) i ``desktop/controllers/request_controller.py``
pozivaju preko duck-typing-a — isti obrazac kao
``dentaland.services.booking.AppointmentService``, ali svaki poziv ide
preko ``DentalandApiClient`` (HTTP), ne lokalne baze.

``awaiting_confirmation``/``cancelled_today`` su NAMJERNO van obima ovog
taska (vidi Task Contract) — vraćaju prazne liste, pa odgovarajuće
sekcije panela uvijek prikazuju "Nema stavki" u daljinskom modu.

Greške (Codex review F1, 30.8.2026): ``DashboardPanels``/
``RequestController`` (dijeljeni sa lokalnom aplikacijom, NE dirani u
ovom tasku) NE očekuju ``ApiClientError`` — samo ``OverlapError``/
``ValueError`` na confirm, i uopšte ništa na doctors/service_choices/
reject_pending poziva (nema try/except tamo). Zato SVE greške ove
klase moraju biti obrađene OVDJE, ne propuštene naviše: liste vraćaju
prazno + poruka, confirm/reject prevode/gutaju grešku uz poruku — GUI
nikad ne padne na server/mrežnu grešku.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QMessageBox

from dentaland.services.availability import OverlapError
from dentaland.services.requests import RequestDTO
from dentaland.services.settings import DoctorDTO
from desktop.api_client import ApiClientError, DentalandApiClient

_TITLE = "Dentaland — daljinski demo"


class RemoteRequestsStore:
    """Vidi modul docstring — uzak "store" samo za panel zahtjeva."""

    def __init__(self, client: DentalandApiClient) -> None:
        self._client = client

    def _warn(self, message: str) -> None:
        QMessageBox.warning(None, _TITLE, message)

    def pending_requests(self) -> list[RequestDTO]:
        try:
            return self._client.get_pending_requests()
        except ApiClientError as exc:
            self._warn(str(exc))
            return []

    def awaiting_confirmation(self) -> list:
        return []

    def cancelled_today(self) -> list:
        return []

    def doctors(self) -> list[DoctorDTO]:
        try:
            return self._client.get_doctors()
        except ApiClientError as exc:
            self._warn(str(exc))
            return []

    def service_choices(self) -> list[tuple[int, str]]:
        try:
            return self._client.get_service_choices()
        except ApiClientError as exc:
            self._warn(str(exc))
            return []

    def confirm_pending(
        self, request_id: int, doctor_id: int, service_id: int, start: datetime
    ) -> None:
        """``OverlapError`` prolazi nepromijenjena (``RequestController``
        je već hvata i prikazuje u dijalogu). Svaka DRUGA greška klijenta
        (mrežna, auth, rate-limit, server) se prevodi u ``ValueError`` —
        isti razlog: postojeći, nepromijenjeni ``RequestController`` već
        hvata i ``ValueError``, pa se poruka prikaže u istom dijalogu bez
        potrebe da se taj dijeljeni kod dira."""
        try:
            self._client.confirm_pending(request_id, doctor_id, service_id, start)
        except OverlapError:
            raise
        except ApiClientError as exc:
            raise ValueError(str(exc)) from exc

    def reject_pending(self, request_id: int) -> None:
        """``RequestController.process_pending_request`` NE hvata ništa oko
        ovog poziva (``return True`` odmah nakon) — greška se zato mora
        obraditi ovdje, ne propustiti naviše. Zahtjev ostaje PENDING na
        serveru ako poziv ne uspije (sljedeći refresh to tačno pokazuje)."""
        try:
            self._client.reject_pending(request_id)
        except ApiClientError as exc:
            self._warn(str(exc))
