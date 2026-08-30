"""Testovi ``desktop/api_client`` (DENT-IMPROVE-020) — httpx.MockTransport,
bez stvarne mreže. Provjerava da klijent ispravno parsira odgovore u
DTO-ove i da SVAKA mrežna/HTTP greška (ne samo 401) završi kao tipiziran
izuzetak iz ovog modula, nikad kao sirov httpx traceback (Codex review F1,
30.8.2026 — vidi agent_reports/2026-08-30-DENT-IMPROVE-020-review-codex.md).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest

from dentaland.services.availability import OverlapError
from desktop.api_client.client import (
    ApiClientError,
    AuthenticationFailedError,
    ConnectionFailedError,
    DentalandApiClient,
    PermissionDeniedError,
    RateLimitedError,
    ServerError,
)


def _client_with_transport(handler) -> DentalandApiClient:
    client = DentalandApiClient("https://test.local")
    client._client = httpx.Client(
        base_url="https://test.local", transport=httpx.MockTransport(handler)
    )
    return client


def _status_handler(status: int, detail: str = "greška"):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": detail})

    return handler


# ---- Centralizovano mapiranje statusa (F1 fix) — svaka metoda koja ne
# posebno obrađuje svoj status (401/403/429/5xx/neočekivan 4xx) mora
# proći kroz isto mapiranje u _request. ----

_STATUS_CASES = [
    (401, AuthenticationFailedError),
    (403, PermissionDeniedError),
    (429, RateLimitedError),
    (500, ServerError),
    (502, ServerError),
    (418, ApiClientError),  # neočekivan status -- i dalje tipiziran, ne sirov
]


@pytest.mark.parametrize(("status", "expected_exc"), _STATUS_CASES)
def test_login_svaki_status_daje_tipiziranu_gresku(status: int, expected_exc: type) -> None:
    client = _client_with_transport(_status_handler(status))
    with pytest.raises(expected_exc):
        client.login("sestra", "lozinka")


@pytest.mark.parametrize(("status", "expected_exc"), _STATUS_CASES)
def test_get_pending_requests_svaki_status_daje_tipiziranu_gresku(
    status: int, expected_exc: type
) -> None:
    client = _client_with_transport(_status_handler(status))
    with pytest.raises(expected_exc):
        client.get_pending_requests()


@pytest.mark.parametrize(("status", "expected_exc"), _STATUS_CASES)
def test_get_doctors_svaki_status_daje_tipiziranu_gresku(status: int, expected_exc: type) -> None:
    client = _client_with_transport(_status_handler(status))
    with pytest.raises(expected_exc):
        client.get_doctors()


@pytest.mark.parametrize(("status", "expected_exc"), _STATUS_CASES)
def test_get_service_choices_svaki_status_daje_tipiziranu_gresku(
    status: int, expected_exc: type
) -> None:
    client = _client_with_transport(_status_handler(status))
    with pytest.raises(expected_exc):
        client.get_service_choices()


@pytest.mark.parametrize(("status", "expected_exc"), _STATUS_CASES)
def test_confirm_pending_ostali_statusi_daju_tipiziranu_gresku(
    status: int, expected_exc: type
) -> None:
    """404/409 imaju posebnu obradu (OverlapError/ValueError, testirano
    odvojeno ispod) — svi OSTALI statusi moraju i dalje proći kroz
    centralno mapiranje, ne sirov httpx."""
    client = _client_with_transport(_status_handler(status))
    with pytest.raises(expected_exc):
        client.confirm_pending(5, doctor_id=1, service_id=2, start=datetime.now(UTC))


@pytest.mark.parametrize(("status", "expected_exc"), _STATUS_CASES)
def test_reject_pending_ostali_statusi_daju_tipiziranu_gresku(
    status: int, expected_exc: type
) -> None:
    client = _client_with_transport(_status_handler(status))
    with pytest.raises(expected_exc):
        client.reject_pending(5)


def test_konekcija_odbijena_baca_connection_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("konekcija odbijena", request=request)

    client = _client_with_transport(handler)
    with pytest.raises(ConnectionFailedError):
        client.login("sestra", "lozinka")


def test_timeout_baca_connection_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    client = _client_with_transport(handler)
    with pytest.raises(ConnectionFailedError):
        client.get_pending_requests()


def test_ostala_httpx_transportna_greska_baca_connection_failed() -> None:
    """Ne samo ConnectError/TimeoutException -- SVAKA httpx.HTTPError
    podklasa mora biti uhvaćena, ne samo dvije najčešće."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadError("konekcija prekinuta usred čitanja", request=request)

    client = _client_with_transport(handler)
    with pytest.raises(ConnectionFailedError):
        client.login("sestra", "lozinka")


def test_greska_sa_ne_json_tijelom_ne_puca_pri_parsiranju_poruke() -> None:
    """Proxy/gateway greška (npr. 502 od nginx-a) često vraća HTML, ne
    JSON -- poruka greške ne smije pucati na tome."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>Bad Gateway</html>")

    client = _client_with_transport(handler)
    with pytest.raises(ServerError):
        client.login("sestra", "lozinka")


# ---- Uspješni odgovori (parsiranje u DTO-ove) ----


def test_login_uspjesan_ne_baca() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/auth/login"
        return httpx.Response(200, json={"username": "sestra", "role": "RECEPTION"})

    client = _client_with_transport(handler)
    client.login("sestra", "lozinka")  # ne smije baciti


def test_get_pending_requests_parsira_u_dto() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "ime": "Ana Anić",
                    "telefon": "061/111-222",
                    "email": "ana@x.com",
                    "requested_date": "2026-08-20",
                    "created_at": "2026-08-19T10:00:00+00:00",
                }
            ],
        )

    client = _client_with_transport(handler)
    rows = client.get_pending_requests()
    assert len(rows) == 1
    assert rows[0].id == 1
    assert rows[0].ime == "Ana Anić"
    assert rows[0].requested_date == date(2026, 8, 20)
    assert rows[0].created_at == datetime(2026, 8, 19, 10, 0, tzinfo=UTC)


def test_get_doctors_parsira_u_dto() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1, "ime": "Ljubo"}])

    client = _client_with_transport(handler)
    doctors = client.get_doctors()
    assert doctors[0].id == 1
    assert doctors[0].ime == "Ljubo"


def test_get_service_choices_vraca_tuple_listu() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[{"id": 1, "naziv": "Kontrola", "trajanje_min": 30, "buffer_min": 0}]
        )

    client = _client_with_transport(handler)
    choices = client.get_service_choices()
    assert choices == [(1, "Kontrola")]


def test_confirm_pending_salje_tacan_payload() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = request.content
        return httpx.Response(204)

    client = _client_with_transport(handler)
    start = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
    client.confirm_pending(5, doctor_id=1, service_id=2, start=start)

    assert captured["method"] == "POST"
    assert captured["path"] == "/api/booking-requests/5/confirm"
    assert b'"doctor_id":1' in captured["body"]
    assert b'"service_id":2' in captured["body"]


def test_confirm_pending_409_baca_overlap_error() -> None:
    client = _client_with_transport(_status_handler(409, "termin se preklapa"))
    with pytest.raises(OverlapError):
        client.confirm_pending(5, doctor_id=1, service_id=2, start=datetime.now(UTC))


def test_confirm_pending_404_baca_value_error() -> None:
    client = _client_with_transport(_status_handler(404, "zahtjev nije pronađen"))
    with pytest.raises(ValueError):
        client.confirm_pending(5, doctor_id=1, service_id=2, start=datetime.now(UTC))


def test_reject_pending_uspjesno_ne_baca() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/booking-requests/5/reject"
        return httpx.Response(204)

    client = _client_with_transport(handler)
    client.reject_pending(5)  # ne smije baciti


def test_reject_pending_404_baca_value_error() -> None:
    client = _client_with_transport(_status_handler(404, "zahtjev nije pronađen"))
    with pytest.raises(ValueError):
        client.reject_pending(999)
