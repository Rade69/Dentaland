"""Testovi email obavještenja pacijentu (DENT-011 + follow-up potvrde)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from dentaland.services import notifications

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


# ---- send_booking_confirmation (zahtjev primljen) ----


def test_bez_emaila_ne_poziva_smtp() -> None:
    with patch("dentaland.services.notifications.smtplib.SMTP") as mock_smtp:
        notifications.send_booking_confirmation("", date(2026, 8, 20))
    mock_smtp.assert_not_called()


def test_bez_smtp_konfiguracije_ne_poziva_smtp() -> None:
    with patch("dentaland.services.notifications.smtplib.SMTP") as mock_smtp:
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))
    mock_smtp.assert_not_called()


def test_salje_email_kada_je_sve_konfigurisano(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch(
        "dentaland.services.notifications.smtplib.SMTP", return_value=instance
    ) as mock_smtp:
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))

    mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
    instance.login.assert_called_once_with("korisnik", "tajna")
    instance.send_message.assert_called_once()
    message = instance.send_message.call_args.args[0]
    assert "ana@x.com" in message["To"]
    assert message["From"] == "no-reply@dentaland.local"


def test_poruka_zahtjev_primljen_sadrzi_samo_dozvoljeni_sadrzaj(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch("dentaland.services.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))

    body = instance.send_message.call_args.args[0].get_content().lower()
    assert "dentaland" in body
    assert "2026-08-20" in body
    assert "kontaktirati" in body
    for zabranjeno in ("kontrola", "ljubo", "zorka", "ana", "usluga", "doktor"):
        assert zabranjeno not in body


def test_smtp_konekcija_greska_ne_baca(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    with patch(
        "dentaland.services.notifications.smtplib.SMTP",
        side_effect=OSError("konekcija pala"),
    ):
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))


def test_slanje_greska_ne_baca(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    instance.send_message.side_effect = RuntimeError("server odbio poruku")
    with patch("dentaland.services.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_booking_confirmation("ana@x.com", date(2026, 8, 20))


# ---- send_appointment_confirmed (termin potvrđen) ----


def test_potvrda_bez_emaila_ne_poziva_smtp() -> None:
    with patch("dentaland.services.notifications.smtplib.SMTP") as mock_smtp:
        notifications.send_appointment_confirmed("", datetime(2026, 8, 20, 9, 0, tzinfo=UTC))
    mock_smtp.assert_not_called()


def test_potvrda_salje_email_kada_je_sve_konfigurisano(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch("dentaland.services.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_appointment_confirmed(
            "ana@x.com", datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        )
    instance.send_message.assert_called_once()
    message = instance.send_message.call_args.args[0]
    assert "ana@x.com" in message["To"]
    assert "potvrđen" in message["Subject"].lower()


def test_poruka_potvrda_sadrzi_tacno_vrijeme_ali_ne_uslugu_ni_doktora(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch("dentaland.services.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_appointment_confirmed(
            "ana@x.com", datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        )

    body = instance.send_message.call_args.args[0].get_content().lower()
    assert "dentaland" in body
    assert "20.08.2026" in body
    assert "11:00" in body  # UTC 09:00 -> Europe/Sarajevo ljetno vrijeme (UTC+2)
    for zabranjeno in ("kontrola", "ljubo", "zorka", "usluga", "doktor"):
        assert zabranjeno not in body


def test_poruka_potvrda_sa_doctor_name_sadrzi_ime_ali_ne_uslugu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Djelimičan izuzetak (Radovan, 30.8.2026) — kad je ``doctor_name``
    eksplicitno proslijeđen, poruka SMIJE ga sadržati. Naziv usluge i
    dalje nema nikakav parametar za to — nema šanse da uđe u poruku."""
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch("dentaland.services.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_appointment_confirmed(
            "ana@x.com", datetime(2026, 8, 20, 9, 0, tzinfo=UTC), doctor_name="Ljubo"
        )

    body = instance.send_message.call_args.args[0].get_content()
    assert "Ljubo" in body
    assert "kontrola" not in body.lower()
    assert "usluga" not in body.lower()


def test_potvrda_smtp_greska_ne_baca(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    with patch(
        "dentaland.services.notifications.smtplib.SMTP",
        side_effect=OSError("konekcija pala"),
    ):
        notifications.send_appointment_confirmed(
            "ana@x.com", datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        )


# ---- send_appointment_reminder (podsjetnik na zakazan termin, DENT-017) ----


def test_podsjetnik_bez_emaila_ne_poziva_smtp() -> None:
    with patch("dentaland.services.notifications.smtplib.SMTP") as mock_smtp:
        notifications.send_appointment_reminder(
            "", datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        )
    mock_smtp.assert_not_called()


def test_podsjetnik_salje_email_kada_konfigurisano(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch("dentaland.services.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_appointment_reminder(
            "ana@x.com", datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        )
    instance.send_message.assert_called_once()
    message = instance.send_message.call_args.args[0]
    assert "ana@x.com" in message["To"]
    assert "podsjetnik" in message["Subject"].lower()


def test_poruka_podsjetnik_sadrzi_tacno_vrijeme_ali_ne_uslugu_ni_doktora(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _postavi_smtp(monkeypatch)
    instance = _smtp_mock()
    with patch("dentaland.services.notifications.smtplib.SMTP", return_value=instance):
        notifications.send_appointment_reminder(
            "ana@x.com", datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        )

    body = instance.send_message.call_args.args[0].get_content().lower()
    assert "dentaland" in body
    assert "20.08.2026" in body
    assert "11:00" in body  # UTC 09:00 -> Europe/Sarajevo ljetno (UTC+2)
    assert "zakazan" in body
    for zabranjeno in ("kontrola", "ljubo", "zorka", "usluga", "doktor"):
        assert zabranjeno not in body


def test_podsjetnik_smtp_greska_ne_baca(monkeypatch: pytest.MonkeyPatch) -> None:
    _postavi_smtp(monkeypatch)
    with patch(
        "dentaland.services.notifications.smtplib.SMTP",
        side_effect=OSError("konekcija pala"),
    ):
        notifications.send_appointment_reminder(
            "ana@x.com", datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        )
