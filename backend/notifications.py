"""Email potvrda pacijentu pri slanju javnog zahtjeva (DENT-011).

Best-effort: slanje emaila nikad ne smije srušiti booking tok — ako SMTP
nije konfigurisan ili slanje ne uspije, funkcija samo loguje razlog i vraća
se bez izuzetka. SMTP kredencijali dolaze isključivo iz env varijabli,
nikad iz koda.

Sadržaj poruke poštuje minimizaciju podataka iz ``CLAUDE.md``: samo ime
ordinacije, traženi datum i poruka o naknadnom kontaktu — NIKAD naziv
usluge ili doktora.
"""

from __future__ import annotations

import logging
import os
import smtplib
from datetime import date
from email.message import EmailMessage

logger = logging.getLogger(__name__)

PRACTICE_NAME = "Dentaland"

_SMTP_TIMEOUT_SECONDS = 10


def send_booking_confirmation(to_email: str, requested_date: date) -> None:
    """Pošalji potvrdu o primljenom zahtjevu — best-effort, nikad ne diže izuzetak.

    Ako pacijent nije unio email ili SMTP nije konfigurisan, samo se loguje
    razlog i preskače slanje. Greška pri slanju se loguje, ali se NE
    propagira — pozivalac (booking endpoint) ostaje netaknut.
    """
    try:
        _send(to_email, requested_date)
    except Exception as exc:
        logger.warning("Slanje email potvrde nije uspjelo (best-effort): %s", exc)


def _send(to_email: str, requested_date: date) -> None:
    address = (to_email or "").strip()
    if not address:
        logger.info("Pacijent nije unio email adresu — nema kome poslati potvrdu.")
        return

    config = _smtp_config()
    if config is None:
        logger.info("SMTP nije konfigurisan (DENTALAND_SMTP_HOST nedostaje) — preskačem slanje.")
        return

    host, port, user, password, from_addr = config
    message = _compose_message(address, requested_date, from_addr)

    with smtplib.SMTP(host, port, timeout=_SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        if user:
            smtp.login(user, password)
        smtp.send_message(message)

    logger.info("Email potvrda uspješno poslana.")


def _smtp_config() -> tuple[str, int, str, str, str] | None:
    """Pročitaj SMTP postavke iz env varijabli; ``None`` ako host nije postavljen."""
    host = os.environ.get("DENTALAND_SMTP_HOST", "").strip()
    if not host:
        return None
    port = int(os.environ.get("DENTALAND_SMTP_PORT", "587"))
    user = os.environ.get("DENTALAND_SMTP_USER", "")
    password = os.environ.get("DENTALAND_SMTP_PASSWORD", "")
    from_addr = os.environ.get("DENTALAND_SMTP_FROM", "") or user or "no-reply@dentaland.local"
    return host, port, user, password, from_addr


def _compose_message(to_email: str, requested_date: date, from_addr: str) -> EmailMessage:
    """Komponuj potvrdu — SAMO ime ordinacije, datum i poruka o naknadnom kontaktu."""
    message = EmailMessage()
    message["Subject"] = f"Zahtjev primljen — {PRACTICE_NAME}"
    message["From"] = from_addr
    message["To"] = to_email
    message.set_content(
        f"Vaš zahtjev za {requested_date.isoformat()} je primljen.\n"
        f"Ordinacija {PRACTICE_NAME} će Vas kontaktirati sa tačnim vremenom termina.\n"
    )
    return message
