"""Telegram bot podsjetnici (DENT-IMPROVE-018).

Zamjena za pauzirani Viber rad (CLAUDE.md, 30.8.2026, "Šta se namjerno
ne gradi unaprijed") — Telegram Bot API nema nikakvu naplatu, uz
prihvaćen kompromis manje rasprostranjenosti kod pacijenata u BiH.

Isti best-effort princip kao ``notifications.py`` (SMTP): bez
konfigurisanih env varijabli, slanje/verifikacija se tiho isključuju —
nikad ne ruše pozivaoca. SVE poruke poštuju CLAUDE.md minimizaciju:
NIKAD naziv usluge ili doktora, samo vrijeme termina.

Opt-in token je uže-namjenski, SAMO za Telegram link — isti sigurnosni
obrazac kao postojeći ``Session.token_hash`` (DENT-IMPROVE-013,
``auth.py``): sirov token (``secrets.token_urlsafe(32)``) se NIKAD ne
upisuje u bazu, čuva se samo SHA-256 heks hash. Jednokratna semantika —
token se briše iz baze nakon uspješne upotrebe (vidi
``consume_link_token`` u ``backend/main.py`` webhook handleru).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from collections.abc import Callable
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from dentaland.models import Appointment, utcnow
from dentaland.timezone import SARAJEVO

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT_SECONDS = 10
_API_BASE = "https://api.telegram.org"

ENV_BOT_TOKEN = "DENTALAND_TELEGRAM_BOT_TOKEN"
ENV_BOT_USERNAME = "DENTALAND_TELEGRAM_BOT_USERNAME"
ENV_WEBHOOK_SECRET = "DENTALAND_TELEGRAM_WEBHOOK_SECRET"


def generate_link_token() -> tuple[str, str]:
    """Vrati (sirov token, SHA-256 heks hash) — isti obrazac kao
    ``Session.token_hash`` (DENT-IMPROVE-013). Sirov token se vraća SAMO
    jednom, pozivalac ga mora odmah upotrijebiti za deep link — ne čuva
    se nigdje osim u tom trenutku."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash


def hash_token(token: str) -> str:
    """Isti hash kao ``generate_link_token`` — koristi webhook handler
    da pretvori primljeni ``/start <token>`` u hash za pretragu baze."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_deep_link(bot_username: str, raw_token: str) -> str:
    """``https://t.me/<bot>?start=<token>`` — klik pokreće razgovor sa
    ``/start <token>`` porukom koju Telegram automatski šalje botu."""
    return f"https://t.me/{bot_username}?start={raw_token}"


def verify_webhook_secret(header_value: str | None, env: dict[str, str] | None = None) -> bool:
    """Provjeri ``X-Telegram-Bot-Api-Secret-Token`` header preko
    ``hmac.compare_digest``. FAIL-CLOSED: bez konfigurisanog
    ``DENTALAND_TELEGRAM_WEBHOOK_SECRET`` uvijek vraća ``False`` (nikad
    fail-open) i loguje upozorenje — razlika u odnosu na SMTP
    best-effort obrazac je namjerna, ovo je javni webhook endpoint."""
    environ = os.environ if env is None else env
    secret = environ.get(ENV_WEBHOOK_SECRET)
    if not secret:
        logger.warning(
            "%s nije postavljen — Telegram webhook verifikacija fail-closed odbija sve.",
            ENV_WEBHOOK_SECRET,
        )
        return False
    if header_value is None:
        return False
    return hmac.compare_digest(header_value, secret)


def send_message(chat_id: str, text: str, env: dict[str, str] | None = None) -> None:
    """Pošalji poruku preko Telegram Bot API ``sendMessage``.

    Best-effort — nikad ne diže izuzetak, isti princip kao
    ``notifications.py`` SMTP slanje. Bez ``DENTALAND_TELEGRAM_BOT_TOKEN``
    tiho preskače (funkcija je isključena dok se ne konfiguriše).
    """
    environ = os.environ if env is None else env
    bot_token = environ.get(ENV_BOT_TOKEN)
    if not bot_token:
        logger.info("%s nije postavljen — Telegram poruka nije poslata.", ENV_BOT_TOKEN)
        return
    try:
        response = httpx.post(
            f"{_API_BASE}/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except Exception as exc:  # best-effort granica, nikad ne ruši pozivaoca
        logger.warning("Slanje Telegram poruke nije uspjelo: %s", exc)


def consume_telegram_link_token(
    session_factory: Callable[[], Session], raw_token: str, chat_id: str
) -> datetime | None:
    """Potroši opt-in token primljen kroz ``/start <token>`` webhook poruku.

    Nađe ``Appointment`` sa odgovarajućim hash-om, još neisteklim rokom, i
    BEZ već upisanog ``telegram_chat_id`` (sprečava ponovnu upotrebu istog
    tokena — jednokratna semantika). Ako nađe: upiše ``chat_id``/
    ``subscribed_at``, OBRIŠE token (hash + rok), vrati ``start_time`` (za
    potvrdnu poruku pozivaoca). Ako ne nađe (nepostojeći/istekao/već
    iskorišten token) — vrati ``None`` TIHO, bez razlikovanja razloga
    (izbjegava curenje informacije o razlogu neuspjeha/token enumeration).
    """
    token_hash = hash_token(raw_token)
    with session_factory() as session:
        appt = session.scalar(
            select(Appointment).where(
                Appointment.telegram_link_token_hash == token_hash,
                Appointment.telegram_link_token_expires_at > utcnow(),
                Appointment.telegram_chat_id.is_(None),
            )
        )
        if appt is None:
            return None
        appt.telegram_chat_id = chat_id
        appt.telegram_subscribed_at = utcnow()
        appt.telegram_link_token_hash = None
        appt.telegram_link_token_expires_at = None
        start_time = appt.start_time
        session.commit()
        return start_time


def format_subscribed_message(start_time: datetime | None) -> str:
    """SAMO vrijeme termina — NIKAD naziv usluge ili doktora (CLAUDE.md
    minimizacija, isti princip kao email poruke u ``notifications.py``)."""
    if start_time is None:
        return "Pretplaćeni ste na Dentaland podsjetnike."
    local = start_time.astimezone(SARAJEVO)
    return (
        f"Pretplaćeni ste na Dentaland podsjetnike. "
        f"Vaš termin je zakazan za {local:%d.%m.%Y.} u {local:%H:%M}."
    )
