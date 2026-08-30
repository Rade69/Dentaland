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
from sqlalchemy import update
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
    except httpx.HTTPStatusError as exc:
        # NIKAD logovati exc direktno (str(exc)/repr(exc)) — httpx URL-uje
        # bot token u putanju (/bot<token>/sendMessage), pa bi se token
        # upisao u log (Codex review F2, 30.8.2026). Samo status kod.
        logger.warning("Slanje Telegram poruke nije uspjelo (HTTP %s).", exc.response.status_code)
    except Exception as exc:  # best-effort granica, nikad ne ruši pozivaoca
        logger.warning("Slanje Telegram poruke nije uspjelo (%s).", type(exc).__name__)


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

    **Atomska konkurentnost (Codex review F3, 30.8.2026)**: prvobitna
    verzija je radila SELECT pa Python izmjene pa COMMIT — dva
    istovremena webhook poziva sa istim tokenom su oba mogla proći
    SELECT provjeru (oba vide ``telegram_chat_id IS NULL``) prije nego
    ijedan commit-uje, i oba bi "potrošila" isti token. Umjesto toga:
    JEDAN atomski ``UPDATE ... WHERE <isti uslovi> RETURNING start_time``.
    Postgres (i SQLite, gdje pisanja i tako serijalizuje jedna
    baza-nivo brava) garantuju da samo JEDNA konkurentna transakcija
    može uspješno pogoditi red koji zadovoljava WHERE — druga transakcija
    (bilo da čeka pa ponovo evaluira WHERE nakon prve, bilo da je
    serijalizovana) jednostavno ne pogodi nijedan red (``rowcount 0``),
    bez obzira na tajming. Vidi
    ``tests/test_telegram_postgres.py::test_konkurentni_pokusaji_isti_token_samo_jedan_uspijeva``
    za adversarni test dvije stvarne konkurentne transakcije.
    """
    token_hash = hash_token(raw_token)
    now = utcnow()
    with session_factory() as session:
        result = session.execute(
            update(Appointment)
            .where(
                Appointment.telegram_link_token_hash == token_hash,
                Appointment.telegram_link_token_expires_at > now,
                Appointment.telegram_chat_id.is_(None),
            )
            .values(
                telegram_chat_id=chat_id,
                telegram_subscribed_at=now,
                telegram_link_token_hash=None,
                telegram_link_token_expires_at=None,
            )
            .returning(Appointment.start_time)
        )
        row = result.first()
        session.commit()
        return row[0] if row is not None else None


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


def format_reminder_message(start_time: datetime) -> str:
    """Stvaran podsjetnik na dan termina (DENT-IMPROVE-021) — ista
    formulacija kao email podsjetnik (``_compose_reminder_message`` u
    ``notifications.py``). SAMO vrijeme termina — NIKAD naziv usluge ili
    doktora (CLAUDE.md minimizacija)."""
    local = start_time.astimezone(SARAJEVO)
    return f"Podsjetnik: imate zakazan termin {local:%d.%m.%Y.} u {local:%H:%M}."
