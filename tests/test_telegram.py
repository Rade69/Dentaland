"""Testovi Telegram bot podsjetnika (DENT-IMPROVE-018)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dentaland.models import Appointment, AppointmentStatus, Base, utcnow
from dentaland.services import telegram

_TELEGRAM_ENV_VARS = [
    telegram.ENV_BOT_TOKEN,
    telegram.ENV_BOT_USERNAME,
    telegram.ENV_WEBHOOK_SECRET,
]


@pytest.fixture(autouse=True)
def _bez_telegram_okruzenja(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _TELEGRAM_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# ---- generate_link_token / hash_token ----


def test_generate_link_token_hash_se_poklapa_sa_hash_token() -> None:
    raw, token_hash = telegram.generate_link_token()
    assert telegram.hash_token(raw) == token_hash


def test_generate_link_token_je_svaki_put_drugaciji() -> None:
    raw1, _ = telegram.generate_link_token()
    raw2, _ = telegram.generate_link_token()
    assert raw1 != raw2


def test_build_deep_link_sadrzi_bot_i_token() -> None:
    link = telegram.build_deep_link("dentaland_bot", "abc123")
    assert link == "https://t.me/dentaland_bot?start=abc123"


# ---- verify_webhook_secret (fail-closed) ----


def test_verify_webhook_secret_fail_closed_bez_konfiguracije() -> None:
    assert telegram.verify_webhook_secret("bilo-sta", env={}) is False


def test_verify_webhook_secret_odbija_pogresan_header() -> None:
    env = {telegram.ENV_WEBHOOK_SECRET: "tajna"}
    assert telegram.verify_webhook_secret("pogresna", env=env) is False


def test_verify_webhook_secret_odbija_nedostajuci_header() -> None:
    env = {telegram.ENV_WEBHOOK_SECRET: "tajna"}
    assert telegram.verify_webhook_secret(None, env=env) is False


def test_verify_webhook_secret_prihvata_tacan_header() -> None:
    env = {telegram.ENV_WEBHOOK_SECRET: "tajna"}
    assert telegram.verify_webhook_secret("tajna", env=env) is True


# ---- send_message (best-effort) ----


def test_send_message_bez_tokena_ne_poziva_http() -> None:
    with patch("dentaland.services.telegram.httpx.post") as mock_post:
        telegram.send_message("123", "poruka", env={})
    mock_post.assert_not_called()


def test_send_message_poziva_telegram_api_kada_konfigurisano() -> None:
    env = {telegram.ENV_BOT_TOKEN: "test-token"}
    mock_response = MagicMock()
    with patch("dentaland.services.telegram.httpx.post", return_value=mock_response) as mock_post:
        telegram.send_message("123", "poruka", env=env)
    mock_post.assert_called_once()
    url = mock_post.call_args.args[0]
    assert "test-token" in url
    assert mock_post.call_args.kwargs["json"] == {"chat_id": "123", "text": "poruka"}


def test_send_message_greska_ne_baca() -> None:
    env = {telegram.ENV_BOT_TOKEN: "test-token"}
    with patch("dentaland.services.telegram.httpx.post", side_effect=OSError("konekcija pala")):
        telegram.send_message("123", "poruka", env=env)


def test_send_message_http_greska_ne_loguje_bot_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Codex review F2 (30.8.2026): httpx.HTTPStatusError string
    reprezentacija sadrži cijeli URL (uključujući bot token u putanji
    /bot<token>/sendMessage) — logovanje `exc` direktno bi upisalo token
    u log. Mora se logovati SAMO status kod, nikad `str(exc)`."""
    env = {telegram.ENV_BOT_TOKEN: "SUPER-TAJNI-TOKEN-123"}
    mock_request = httpx.Request(
        "POST", "https://api.telegram.org/botSUPER-TAJNI-TOKEN-123/sendMessage"
    )
    mock_response = httpx.Response(404, request=mock_request)
    error = httpx.HTTPStatusError("404 error", request=mock_request, response=mock_response)

    with patch("dentaland.services.telegram.httpx.post", side_effect=error), caplog.at_level(
        "WARNING"
    ):
        telegram.send_message("123", "poruka", env=env)

    assert "SUPER-TAJNI-TOKEN-123" not in caplog.text


def test_send_message_ostala_greska_ne_loguje_bot_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Isto i za ne-HTTP greške (npr. httpx.ConnectError) — token je i
    tu dio URL-a koji bi neke httpx greške uključile u str(exc)."""
    env = {telegram.ENV_BOT_TOKEN: "SUPER-TAJNI-TOKEN-123"}
    error = httpx.ConnectError(
        "konekcija odbijena ka https://api.telegram.org/botSUPER-TAJNI-TOKEN-123/sendMessage"
    )

    with patch("dentaland.services.telegram.httpx.post", side_effect=error), caplog.at_level(
        "WARNING"
    ):
        telegram.send_message("123", "poruka", env=env)

    assert "SUPER-TAJNI-TOKEN-123" not in caplog.text


# ---- format_subscribed_message (minimizacija) ----


def test_format_subscribed_message_sadrzi_samo_vrijeme() -> None:
    text = telegram.format_subscribed_message(datetime(2026, 8, 20, 9, 0, tzinfo=UTC))
    assert "20.08.2026" in text
    assert "11:00" in text  # UTC 09:00 -> Europe/Sarajevo ljetno vrijeme (UTC+2)
    for zabranjeno in ("kontrola", "ljubo", "zorka", "ana", "usluga", "doktor"):
        assert zabranjeno not in text.lower()


def test_format_subscribed_message_bez_vremena_ne_baca() -> None:
    text = telegram.format_subscribed_message(None)
    assert "Dentaland" in text


# ---- consume_telegram_link_token ----


@pytest.fixture()
def engine() -> Engine:
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def _napravi_zakazan_termin_sa_tokenom(
    session_factory: sessionmaker[Session],
    raw_token: str,
    *,
    expired: bool = False,
    already_used: bool = False,
) -> int:
    start = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
    with session_factory() as session:
        appt = Appointment(
            ime="Ana",
            telefon="061",
            email="ana@x.com",
            start_time=start,
            end_time=start + timedelta(minutes=30),
            status=AppointmentStatus.SCHEDULED,
            telegram_link_token_hash=telegram.hash_token(raw_token),
            telegram_link_token_expires_at=(
                utcnow() - timedelta(hours=1) if expired else utcnow() + timedelta(hours=1)
            ),
            telegram_chat_id="already-subscribed" if already_used else None,
        )
        session.add(appt)
        session.commit()
        return appt.id


def test_consume_token_validan_upisuje_chat_id_i_brise_token(
    session_factory: sessionmaker[Session],
) -> None:
    appt_id = _napravi_zakazan_termin_sa_tokenom(session_factory, "raw-token-1")

    start_time = telegram.consume_telegram_link_token(session_factory, "raw-token-1", "555")

    assert start_time == datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        assert appt.telegram_chat_id == "555"
        assert appt.telegram_subscribed_at is not None
        assert appt.telegram_link_token_hash is None
        assert appt.telegram_link_token_expires_at is None


def test_consume_token_je_jednokratan(session_factory: sessionmaker[Session]) -> None:
    _napravi_zakazan_termin_sa_tokenom(session_factory, "raw-token-2")
    telegram.consume_telegram_link_token(session_factory, "raw-token-2", "555")

    drugi_pokusaj = telegram.consume_telegram_link_token(session_factory, "raw-token-2", "666")

    assert drugi_pokusaj is None


def test_consume_token_nepostojeci_vraca_none(session_factory: sessionmaker[Session]) -> None:
    assert telegram.consume_telegram_link_token(session_factory, "ne-postoji", "555") is None


def test_consume_token_istekao_vraca_none(session_factory: sessionmaker[Session]) -> None:
    _napravi_zakazan_termin_sa_tokenom(session_factory, "raw-token-3", expired=True)
    assert telegram.consume_telegram_link_token(session_factory, "raw-token-3", "555") is None


def test_consume_token_vec_iskoristen_chat_vraca_none(
    session_factory: sessionmaker[Session],
) -> None:
    _napravi_zakazan_termin_sa_tokenom(session_factory, "raw-token-4", already_used=True)
    assert telegram.consume_telegram_link_token(session_factory, "raw-token-4", "555") is None


# ---- webhook endpoint (backend/main.py) ----


@pytest.fixture()
def client(session_factory: sessionmaker[Session]):
    from backend.main import app, get_session_factory, limiter

    app.dependency_overrides[get_session_factory] = lambda: session_factory
    limiter.reset()
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_webhook_bez_secret_konfiguracije_vraca_403(client: TestClient) -> None:
    response = client.post("/api/telegram/webhook", json={})
    assert response.status_code == 403


def test_webhook_pogresan_secret_header_vraca_403(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(telegram.ENV_WEBHOOK_SECRET, "tajna")
    response = client.post(
        "/api/telegram/webhook",
        json={},
        headers={"X-Telegram-Bot-Api-Secret-Token": "pogresna"},
    )
    assert response.status_code == 403


def test_webhook_neispravan_json_sa_pogresnim_secretom_vraca_403_ne_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex review F1 (30.8.2026): tijelo se NE smije parsirati prije
    secret provjere — neispravan JSON uz neispravan secret mora i dalje
    dati 403 (autentifikacija prva), ne 422 koji bi otkrio da je body
    parsiranje uopšte pokušano prije provjere."""
    monkeypatch.setenv(telegram.ENV_WEBHOOK_SECRET, "tajna")
    response = client.post(
        "/api/telegram/webhook",
        content=b"ovo nije validan JSON{{{",
        headers={
            "X-Telegram-Bot-Api-Secret-Token": "pogresna",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 403


def test_webhook_neispravan_json_sa_tacnim_secretom_ne_puca(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nakon uspješne secret provjere, neispravan JSON se tiho ignoriše
    (200), ne 500/ruši endpoint (Telegram uvijek šalje validan JSON, ali
    endpoint ne smije pretpostaviti to bez provjere)."""
    monkeypatch.setenv(telegram.ENV_WEBHOOK_SECRET, "tajna")
    response = client.post(
        "/api/telegram/webhook",
        content=b"ovo nije validan JSON{{{",
        headers={
            "X-Telegram-Bot-Api-Secret-Token": "tajna",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200


def test_webhook_validan_token_upisuje_chat_id_i_salje_poruku(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(telegram.ENV_WEBHOOK_SECRET, "tajna")
    monkeypatch.setenv(telegram.ENV_BOT_TOKEN, "bot-token")
    appt_id = _napravi_zakazan_termin_sa_tokenom(session_factory, "raw-token-ok")

    with patch("dentaland.services.telegram.httpx.post") as mock_post:
        response = client.post(
            "/api/telegram/webhook",
            json={"message": {"text": "/start raw-token-ok", "chat": {"id": 777}}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "tajna"},
        )

    assert response.status_code == 200
    mock_post.assert_called_once()
    with session_factory() as session:
        appt = session.get(Appointment, appt_id)
        assert appt.telegram_chat_id == "777"


def test_webhook_nevazeci_token_tiho_ignorise_ne_salje_poruku(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(telegram.ENV_WEBHOOK_SECRET, "tajna")
    monkeypatch.setenv(telegram.ENV_BOT_TOKEN, "bot-token")

    with patch("dentaland.services.telegram.httpx.post") as mock_post:
        response = client.post(
            "/api/telegram/webhook",
            json={"message": {"text": "/start ne-postoji-token", "chat": {"id": 777}}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "tajna"},
        )

    assert response.status_code == 200
    mock_post.assert_not_called()


def test_webhook_poruka_bez_start_teksta_ne_pravi_nista(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(telegram.ENV_WEBHOOK_SECRET, "tajna")
    response = client.post(
        "/api/telegram/webhook",
        json={"message": {"text": "zdravo", "chat": {"id": 777}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "tajna"},
    )
    assert response.status_code == 200
