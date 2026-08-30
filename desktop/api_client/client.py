"""``DentalandApiClient`` — tanak httpx omotač oko backend API-ja
(DENT-IMPROVE-020).

Session cookie (RBAC, DENT-IMPROVE-013) se čuva automatski unutar
``httpx.Client`` instance preko poziva — ista instanca mora se koristiti
za ``login`` i sve naredne pozive.

Sve mrežne/HTTP greške se pretvaraju u jasne izuzetke iz ovog modula —
GUI sloj (``desktop/remote_demo.py``) nikad ne vidi sirov ``httpx``
traceback.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from dentaland.services.availability import OverlapError
from dentaland.services.requests import RequestDTO
from dentaland.services.settings import DoctorDTO

_TIMEOUT_SECONDS = 10


class ApiClientError(Exception):
    """Bazna klasa za sve greške ovog klijenta."""


class ConnectionFailedError(ApiClientError):
    """Server nedostupan (timeout, DNS, konekcija odbijena)."""


class AuthenticationFailedError(ApiClientError):
    """Pogrešno korisničko ime/lozinka, ili istekla/nepostojeća sesija."""


class DentalandApiClient:
    """Jedna instanca = jedna prijavljena sesija (cookie jar unutar
    ``httpx.Client``). Ne dijeliti između više korisnika/prijava."""

    def __init__(self, base_url: str) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=_TIMEOUT_SECONDS)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DentalandApiClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)  # type: ignore[arg-type]
        except httpx.ConnectError as exc:
            raise ConnectionFailedError(f"Server nedostupan: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionFailedError(f"Server ne odgovara na vrijeme: {exc}") from exc
        if response.status_code == 401:
            raise AuthenticationFailedError("Neispravna prijava ili istekla sesija.")
        return response

    def login(self, username: str, password: str) -> None:
        response = self._request(
            "POST", "/api/auth/login", json={"username": username, "password": password}
        )
        if response.status_code != 200:
            raise AuthenticationFailedError("Neispravno korisničko ime ili lozinka.")

    def get_pending_requests(self) -> list[RequestDTO]:
        response = self._request("GET", "/api/booking-requests")
        response.raise_for_status()
        return [
            RequestDTO(
                id=row["id"],
                ime=row["ime"],
                telefon=row["telefon"],
                email=row["email"],
                requested_date=datetime.fromisoformat(row["requested_date"]).date(),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in response.json()
        ]

    def get_doctors(self) -> list[DoctorDTO]:
        response = self._request("GET", "/api/doctors")
        response.raise_for_status()
        return [DoctorDTO(id=row["id"], ime=row["ime"]) for row in response.json()]

    def get_service_choices(self) -> list[tuple[int, str]]:
        response = self._request("GET", "/api/services")
        response.raise_for_status()
        return [(row["id"], row["naziv"]) for row in response.json()]

    def confirm_pending(
        self, request_id: int, doctor_id: int, service_id: int, start: datetime
    ) -> None:
        response = self._request(
            "POST",
            f"/api/booking-requests/{request_id}/confirm",
            json={
                "doctor_id": doctor_id,
                "service_id": service_id,
                "start_time": start.isoformat(),
            },
        )
        if response.status_code == 409:
            raise OverlapError(response.json().get("detail", "Termin se preklapa."))
        if response.status_code == 404:
            raise ValueError(response.json().get("detail", "Zahtjev nije pronađen."))
        response.raise_for_status()

    def reject_pending(self, request_id: int) -> None:
        response = self._request("POST", f"/api/booking-requests/{request_id}/reject")
        if response.status_code == 404:
            raise ValueError(response.json().get("detail", "Zahtjev nije pronađen."))
        response.raise_for_status()
