"""Testovi ``desktop/remote_store.py`` (DENT-IMPROVE-020) — potvrđuje da
greške iz ``DentalandApiClient`` NIKAD ne cure neobrađene ka
``DashboardPanels``/``RequestController`` (dijeljeni sa lokalnom
aplikacijom, nepromijenjeni u ovom tasku — vidi Codex review F1,
30.8.2026, `agent_reports/2026-08-30-DENT-IMPROVE-020-review-codex.md`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from dentaland.services.availability import OverlapError
from desktop.api_client import (
    AuthenticationFailedError,
    ConnectionFailedError,
    ServerError,
)
from desktop.remote_store import RemoteRequestsStore


def _store_with_client(**overrides) -> tuple[RemoteRequestsStore, MagicMock]:
    client = MagicMock()
    for name, value in overrides.items():
        getattr(client, name).side_effect = value
    return RemoteRequestsStore(client), client


def test_pending_requests_uspjeh_prosljedjuje_rezultat() -> None:
    store, client = _store_with_client()
    client.get_pending_requests.return_value = ["a", "b"]
    assert store.pending_requests() == ["a", "b"]


def test_pending_requests_greska_vraca_prazno_i_prikazuje_poruku() -> None:
    store, _ = _store_with_client(get_pending_requests=ConnectionFailedError("server pao"))
    with patch("desktop.remote_store.QMessageBox.warning") as warn:
        result = store.pending_requests()
    assert result == []
    warn.assert_called_once()


def test_doctors_greska_vraca_prazno_i_prikazuje_poruku() -> None:
    store, _ = _store_with_client(get_doctors=ServerError("500"))
    with patch("desktop.remote_store.QMessageBox.warning") as warn:
        result = store.doctors()
    assert result == []
    warn.assert_called_once()


def test_service_choices_greska_vraca_prazno_i_prikazuje_poruku() -> None:
    store, _ = _store_with_client(get_service_choices=AuthenticationFailedError("istekla sesija"))
    with patch("desktop.remote_store.QMessageBox.warning") as warn:
        result = store.service_choices()
    assert result == []
    warn.assert_called_once()


def test_awaiting_confirmation_i_cancelled_today_su_uvijek_prazni() -> None:
    store, _ = _store_with_client()
    assert store.awaiting_confirmation() == []
    assert store.cancelled_today() == []


def test_confirm_pending_overlap_error_prolazi_nepromijenjen() -> None:
    """RequestController već hvata OverlapError -- ne smije se prevesti
    u nešto drugo, mora proći kroz kao takav."""
    store, _ = _store_with_client(confirm_pending=OverlapError("preklapa se"))
    with pytest.raises(OverlapError):
        store.confirm_pending(1, doctor_id=1, service_id=1, start=datetime.now(UTC))


def test_confirm_pending_ostale_greske_postaju_value_error() -> None:
    """RequestController hvata i ValueError -- svaka DRUGA ApiClientError
    (mrežna, auth, server...) se zato prevodi u ValueError da postojeći,
    nepromijenjeni RequestController prikaže poruku bez izmjene."""
    store, _ = _store_with_client(confirm_pending=ServerError("500"))
    with pytest.raises(ValueError):
        store.confirm_pending(1, doctor_id=1, service_id=1, start=datetime.now(UTC))


def test_confirm_pending_uspjeh_ne_baca() -> None:
    store, client = _store_with_client()
    client.confirm_pending.return_value = None
    store.confirm_pending(1, doctor_id=1, service_id=1, start=datetime.now(UTC))


def test_reject_pending_greska_ne_baca_prikazuje_poruku() -> None:
    """RequestController NE hvata ništa oko reject_pending poziva --
    greška se MORA obraditi ovdje, ne propustiti naviše (inače puca kroz
    dugme klik handler)."""
    store, _ = _store_with_client(reject_pending=ConnectionFailedError("server pao"))
    with patch("desktop.remote_store.QMessageBox.warning") as warn:
        store.reject_pending(1)  # ne smije baciti
    warn.assert_called_once()


def test_reject_pending_uspjeh_ne_baca() -> None:
    store, client = _store_with_client()
    client.reject_pending.return_value = None
    store.reject_pending(1)
