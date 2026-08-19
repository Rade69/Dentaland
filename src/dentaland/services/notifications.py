"""Email obavještenja pacijentu (DENT-011 + follow-up).

Premješteno iz ``backend/notifications.py`` (18.8.2026) — servisni sloj
je dijeljen između backend API-ja i desktop aplikacije
(``confirm_request()`` u ``requests.py`` se poziva sa oba mjesta), pa
slanje email obavještenja mora živjeti ovdje, ne pod ``backend/``, da bi
radilo bez obzira ko potvrdi zahtjev (backend API ili desktop dashboard).

Best-effort: slanje emaila nikad ne smije srušiti booking/potvrda tok —
ako SMTP nije konfigurisan ili slanje ne uspije, funkcija samo loguje
razlog i vraća se bez izuzetka. SMTP kredencijali dolaze isključivo iz
env varijabli, nikad iz koda.

Sadržaj poruka poštuje minimizaciju podataka iz ``CLAUDE.md``: ime
ordinacije, datum (i za potvrđen termin: tačno vrijeme — dozvoljeno
pravilom "nikad naziv usluge, samo vrijeme termina") — NIKAD naziv
usluge ili doktora.
"""

from __future__ import annotations

import logging
import os
import smtplib
from collections.abc import Callable
from datetime import date, datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

PRACTICE_NAME = "Dentaland"
SARAJEVO = ZoneInfo("Europe/Sarajevo")

_SMTP_TIMEOUT_SECONDS = 10


def send_booking_confirmation(to_email: str, requested_date: date) -> None:
    """Pošalji potvrdu o PRIMLJENOM zahtjevu — best-effort, nikad ne diže izuzetak."""
    try:
        _dispatch(to_email, lambda addr, from_addr: _compose_received_message(
            addr, requested_date, from_addr
        ))
    except Exception as exc:
        logger.warning("Slanje email potvrde (zahtjev primljen) nije uspjelo: %s", exc)


def send_appointment_confirmed(to_email: str, start_time: datetime) -> None:
    """Pošalji obavještenje da je termin POTVRĐEN sa tačnim vremenom.

    Isti best-effort princip — nikad ne diže izuzetak, pozivalac
    (``confirm_request``) ostaje netaknut bez obzira na SMTP ishod.
    """
    try:
        _dispatch(to_email, lambda addr, from_addr: _compose_confirmed_message(
            addr, start_time, from_addr
        ))
    except Exception as exc:
        logger.warning("Slanje email potvrde (termin potvrđen) nije uspjelo: %s", exc)


def send_appointment_reminder(to_email: str, start_time: datetime) -> None:
    """Pošalji podsjetnik na zakazan termin — best-effort, nikad ne diže.

    Servisna funkcija (DENT-017): poziva je scheduler/pozivalac sa poznatim
    appointment podacima. Scheduler/cron je VAN obima ovog taska. Poruka
    sadrži SAMO ime ordinacije i tačno vrijeme termina — NIKAD uslugu ni
    doktora (minimizacija). Rečenica o linku za izmjenu se namjerno
    izostavlja dok ne postoji siguran cancel/reschedule token mehanizam.
    """
    try:
        _dispatch(to_email, lambda addr, from_addr: _compose_reminder_message(
            addr, start_time, from_addr
        ))
    except Exception as exc:
        logger.warning("Slanje email podsjetnika nije uspjelo: %s", exc)


def _dispatch(to_email: str, compose: Callable[[str, str], EmailMessage]) -> None:
    address = (to_email or "").strip()
    if not address:
        logger.info("Pacijent nije unio email adresu — nema kome poslati obavještenje.")
        return

    config = _smtp_config()
    if config is None:
        logger.info("SMTP nije konfigurisan (DENTALAND_SMTP_HOST nedostaje) — preskačem slanje.")
        return

    host, port, user, password, from_addr = config
    message = compose(address, from_addr)

    with smtplib.SMTP(host, port, timeout=_SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        if user:
            smtp.login(user, password)
        smtp.send_message(message)

    logger.info("Email obavještenje uspješno poslano.")


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


def _compose_received_message(to_email: str, requested_date: date, from_addr: str) -> EmailMessage:
    """SAMO ime ordinacije, traženi datum i poruka o naknadnom kontaktu."""
    message = EmailMessage()
    message["Subject"] = f"Zahtjev primljen — {PRACTICE_NAME}"
    message["From"] = from_addr
    message["To"] = to_email
    message.set_content(
        f"Vaš zahtjev za {requested_date.isoformat()} je primljen.\n"
        f"Ordinacija {PRACTICE_NAME} će Vas kontaktirati sa tačnim vremenom termina.\n"
    )
    return message


def _compose_confirmed_message(to_email: str, start_time: datetime, from_addr: str) -> EmailMessage:
    """SAMO ime ordinacije i tačno vrijeme — NIKAD usluga ili doktor."""
    local = start_time.astimezone(SARAJEVO)
    message = EmailMessage()
    message["Subject"] = f"Termin potvrđen — {PRACTICE_NAME}"
    message["From"] = from_addr
    message["To"] = to_email
    message.set_content(
        f"Vaš termin je potvrđen za {local:%d.%m.%Y.} u {local:%H:%M}.\n"
        f"Ordinacija {PRACTICE_NAME} Vas očekuje.\n"
    )
    return message


def _compose_reminder_message(to_email: str, start_time: datetime, from_addr: str) -> EmailMessage:
    """Podsjetnik — SAMO ime ordinacije i tačno vrijeme, NIKAD usluga/doktor."""
    local = start_time.astimezone(SARAJEVO)
    message = EmailMessage()
    message["Subject"] = f"Podsjetnik na termin — {PRACTICE_NAME}"
    message["From"] = from_addr
    message["To"] = to_email
    message.set_content(
        f"{PRACTICE_NAME}: imate zakazan termin {local:%d.%m.%Y.} u {local:%H:%M}.\n"
        f"Ordinacija {PRACTICE_NAME} Vas očekuje.\n"
    )
    return message
