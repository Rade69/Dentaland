"""Testovi email potvrde za javne zahtjeve (DENT-011)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from backend import notifications

_SMTP_ENV_VARS = [
    "DENTALAND_SMTP_HOST",
    "DENTALAND_SMTP_PORT",
    "DENTALAND_SMTP_USER",
    "DENTALAND_SMTP_PASSWORD",
    "DENTALAND_SMTP_FROM",
]


@pytest.fixture(autouse=True)
def _bez_smtp_okruzenja(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _SMTP_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _postavi_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DENTALAND_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("DENTALAND_SMTP_PORT", "587")
    monkeypatch.setenv("DENTALAND_SMTP_USER", "korisnik")
    monkeypatch.setenv("DENTALAND_SMTP_PASSWORD", "tajna")
    monkeypatch.setenv("DENTALAND_SMTP_FROM", "no-reply@dentaland.local")


def _smtp_mock() -> MagicMock:
    """Mock koji se ponaša kao kontekstni menadžer (SMTP.__enter__ vraća self)."""
    instance = MagicMock()
    instance.__enter__.return_value = instance
    return instance


def test_bez_emaila_ne_poziva_smtp() -> None:
    with patch("backend.notifications.smtplib.SMTP") as mock_smtp:
        notifications.send_booking_confirmation("", date(2026, 8, 20))
    mock_smtp.assert_not_called()


def test_bez_smtp_konfiguracije_ne_poziva_smtp() -> None:
    with patch("backend.notifications.smtplib.SMTP") as mock_smtp:
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))
    mock_smtp.assert_not_called()


def test_salje_email_kada_je_sve_konfigurisano(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch("backend.notifications.smtplib.SMTP", return_value=instance) as mock_smtp:
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))

    mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
    instance.login.assert_called_once_with("korisnik", "tajna")
    instance.send_message.assert_called_once()
    message = instance.send_message.call_args.args[0]
    assert "ana@x.com" in message["To"]
    assert message["From"] == "no-reply@dentaland.local"


def test_poruka_sadrzi_samo_dozvoljeni_sadrzaj(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch("backend.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))

    body = instance.send_message.call_args.args[0].get_content().lower()
    assert "dentaland" in body
    assert "2026-08-20" in body
    assert "kontaktirati" in body
    for zabranjeno in ("kontrola", "ljubo", "zorka", "ana", "usluga", "doktor"):
        assert zabranjeno not in body


def test_smtp_konekcija_greska_ne_baca(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    with patch("backend.notifications.smtplib.SMTP", side_effect=OSError("konekcija pala")):
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))


def test_slanje_greska_ne_baca(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    instance.send_message.side_effect = RuntimeError("server odbio poruku")
    with patch("backend.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))
