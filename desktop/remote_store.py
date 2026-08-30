""""Store" adapter za daljinski demo (DENT-IMPROVE-020).

Implementira TAČNO metode koje ``desktop/views/requests_panel.py``
(``DashboardPanels``) i ``desktop/controllers/request_controller.py``
pozivaju preko duck-typing-a — isti obrazac kao
``dentaland.services.booking.AppointmentService``, ali svaki poziv ide
preko ``DentalandApiClient`` (HTTP), ne lokalne baze.

``awaiting_confirmation``/``cancelled_today`` su NAMJERNO van obima ovog
taska (vidi Task Contract) — vraćaju prazne liste, pa odgovarajuće
sekcije panela uvijek prikazuju "Nema stavki" u daljinskom modu.
"""

from __future__ import annotations

from datetime import datetime

from dentaland.services.requests import RequestDTO
from dentaland.services.settings import DoctorDTO
from desktop.api_client import DentalandApiClient


class RemoteRequestsStore:
    """Vidi modul docstring — uzak "store" samo za panel zahtjeva."""

    def __init__(self, client: DentalandApiClient) -> None:
        self._client = client

    def pending_requests(self) -> list[RequestDTO]:
        return self._client.get_pending_requests()

    def awaiting_confirmation(self) -> list:
        return []

    def cancelled_today(self) -> list:
        return []

    def doctors(self) -> list[DoctorDTO]:
        return self._client.get_doctors()

    def service_choices(self) -> list[tuple[int, str]]:
        return self._client.get_service_choices()

    def confirm_pending(
        self, request_id: int, doctor_id: int, service_id: int, start: datetime
    ) -> None:
        self._client.confirm_pending(request_id, doctor_id, service_id, start)

    def reject_pending(self, request_id: int) -> None:
        self._client.reject_pending(request_id)
