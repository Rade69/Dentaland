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
    """Bazna klasa za sve greške ovog klijenta — SVAKI status kod i
    svaka mrežna greška završava kao neki podtip ove klase (ili baza
    direktno za neočekivane statuse), nikad kao sirov ``httpx``
    izuzetak (DENT-IMPROVE-020, Codex review F1, 30.8.2026)."""


class ConnectionFailedError(ApiClientError):
    """Server nedostupan (timeout, DNS, konekcija odbijena, ili bilo
    koja druga ``httpx`` transportna greška)."""


class AuthenticationFailedError(ApiClientError):
    """Pogrešno korisničko ime/lozinka, ili istekla/nepostojeća sesija (401)."""


class PermissionDeniedError(ApiClientError):
    """Prijavljen, ali bez RECEPTION uloge (403)."""


class RateLimitedError(ApiClientError):
    """Previše zahtjeva u kratkom periodu (429) — vidi ``slowapi`` limite
    na svakom endpointu, `backend/main.py`."""


class ServerError(ApiClientError):
    """Backend je vratio 5xx grešku."""


def _error_detail(response: httpx.Response) -> str:
    """Izvuci ``detail`` iz JSON tijela ako postoji — tijelo grešnog
    odgovora ne mora uvijek biti validan JSON (npr. proxy/gateway
    greška), pa se ovo NIKAD ne smije osloniti na to bez zaštite."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return response.text[:200]


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

    def _request(
        self, method: str, path: str, *, expect: frozenset[int] = frozenset(), **kwargs: object
    ) -> httpx.Response:
        """Izvrši zahtjev i centralno prevedi SVAKU grešku (mrežnu ili
        HTTP status) u tipiziran izuzetak iz ovog modula.

        ``expect`` je skup statusa koje pozivalac SAM želi obraditi
        (npr. ``confirm_pending`` posebno tretira 404/409) — ti statusi
        se vraćaju pozivaocu neobrađeni, SVI ostali ne-2xx statusi
        (401/403/429/5xx/bilo koji drugi) se ovdje pretvaraju u jasan
        izuzetak, nikad ne cure kao sirov ``httpx.HTTPStatusError``.
        """
        try:
            response = self._client.request(method, path, **kwargs)  # type: ignore[arg-type]
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ConnectionFailedError(f"Server nedostupan: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ConnectionFailedError(f"Mrežna greška: {exc}") from exc

        if response.status_code in expect:
            return response
        if response.status_code // 100 == 2:
            return response
        if response.status_code == 401:
            raise AuthenticationFailedError("Neispravna prijava ili istekla sesija.")
        if response.status_code == 403:
            raise PermissionDeniedError("Nemaš ovlaštenje za ovu radnju.")
        if response.status_code == 429:
            raise RateLimitedError("Previše zahtjeva u kratkom periodu — sačekaj malo.")
        if response.status_code >= 500:
            raise ServerError(f"Server greška ({response.status_code}).")
        raise ApiClientError(
            f"Neočekivan odgovor servera ({response.status_code}): {_error_detail(response)}"
        )

    def login(self, username: str, password: str) -> None:
        self._request(
            "POST", "/api/auth/login", json={"username": username, "password": password}
        )

    def get_pending_requests(self) -> list[RequestDTO]:
        response = self._request("GET", "/api/booking-requests")
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
        return [DoctorDTO(id=row["id"], ime=row["ime"]) for row in response.json()]

    def get_service_choices(self) -> list[tuple[int, str]]:
        response = self._request("GET", "/api/services")
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
            expect=frozenset({404, 409}),
        )
        if response.status_code == 409:
            raise OverlapError(_error_detail(response))
        if response.status_code == 404:
            raise ValueError(_error_detail(response))

    def reject_pending(self, request_id: int) -> None:
        response = self._request(
            "POST", f"/api/booking-requests/{request_id}/reject", expect=frozenset({404})
        )
        if response.status_code == 404:
            raise ValueError(_error_detail(response))
