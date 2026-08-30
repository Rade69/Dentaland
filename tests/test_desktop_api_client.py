"""Testovi ``desktop/api_client`` (DENT-IMPROVE-020) — httpx.MockTransport,
bez stvarne mreže. Provjerava da klijent ispravno parsira odgovore u
DTO-ove i da mrežne/HTTP greške ne cure kao sirov httpx traceback."""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest

from dentaland.services.availability import OverlapError
from desktop.api_client.client import (
    AuthenticationFailedError,
    ConnectionFailedError,
    DentalandApiClient,
)


def _client_with_transport(handler) -> DentalandApiClient:
    client = DentalandApiClient("https://test.local")
    client._client = httpx.Client(
        base_url="https://test.local", transport=httpx.MockTransport(handler)
    )
    return client


def test_login_uspjesan_ne_baca() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/auth/login"
        return httpx.Response(200, json={"username": "sestra", "role": "RECEPTION"})

    client = _client_with_transport(handler)
    client.login("sestra", "lozinka")  # ne smije baciti


def test_login_pogresna_lozinka_baca_authentication_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "pogrešno korisničko ime ili lozinka"})

    client = _client_with_transport(handler)
    with pytest.raises(AuthenticationFailedError):
        client.login("sestra", "pogresna")


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


def test_get_pending_requests_bez_prijave_baca_authentication_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "nije prijavljen"})

    client = _client_with_transport(handler)
    with pytest.raises(AuthenticationFailedError):
        client.get_pending_requests()


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
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": "termin se preklapa"})

    client = _client_with_transport(handler)
    with pytest.raises(OverlapError):
        client.confirm_pending(5, doctor_id=1, service_id=2, start=datetime.now(UTC))


def test_confirm_pending_404_baca_value_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "zahtjev nije pronađen"})

    client = _client_with_transport(handler)
    with pytest.raises(ValueError):
        client.confirm_pending(5, doctor_id=1, service_id=2, start=datetime.now(UTC))


def test_reject_pending_uspjesno_ne_baca() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/booking-requests/5/reject"
        return httpx.Response(204)

    client = _client_with_transport(handler)
    client.reject_pending(5)  # ne smije baciti


def test_reject_pending_404_baca_value_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "zahtjev nije pronađen"})

    client = _client_with_transport(handler)
    with pytest.raises(ValueError):
        client.reject_pending(999)
