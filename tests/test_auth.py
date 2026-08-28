"""Testovi autentifikacije + RBAC (DENT-IMPROVE-013).

`TestClient` MORA koristiti `base_url="https://testserver"` — login cookie
je `Secure`, a httpx-ov cookie jar (poštuje RFC 6265 semantiku) ne šalje
`Secure` kolačiće nazad na plain `http://` vezu. Ovo je standardan obrazac
za testiranje secure cookieja kroz Starlette `TestClient`, ne workaround
oko stvarnog ponašanja.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import SESSION_COOKIE_NAME, app, get_session_factory, limiter
from dentaland.models import Base, User, UserRole
from dentaland.services.auth import hash_password, invalidate_all_sessions_for_user


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


@pytest.fixture()
def client(session_factory: sessionmaker[Session]):
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    # `limiter` je modul-nivo singleton (dijeljen preko CIJELE pytest sesije,
    # ne po testu) — bez reset-a, kvota od prethodnih testova (uključujući
    # namjerno-iscrpljujuće rate-limit testove) bi curila u naredne testove.
    limiter.reset()
    # base_url="https://..." — vidi napomenu u docstringu modula.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _make_user(
    session_factory: sessionmaker[Session],
    username: str,
    password: str,
    role: UserRole,
) -> int:
    with session_factory() as session:
        user = User(username=username, password_hash=hash_password(password), role=role)
        session.add(user)
        session.commit()
        return user.id


def _login(client: TestClient, username: str, password: str):
    return client.post("/api/auth/login", json={"username": username, "password": password})


# --- Password hashing: Argon2id (Pi review N1) --------------------------


def test_hash_password_koristi_argon2id() -> None:
    """v3.1 eksplicitno traži Argon2id (ne bcrypt/passlib default). Pi review
    N1: ranije je ovo bilo potvrđeno samo ručno u izvještaju, ne trajnim
    testom — ovaj assert na `$argon2id$` prefiks (PHC string format koji
    argon2-cffi generiše) čuva taj zahtjev kao regresionu zaštitu."""
    hashed = hash_password("bilo-koja-lozinka")
    assert hashed.startswith("$argon2id$")
    assert hashed != "bilo-koja-lozinka"


# --- Login: uspjeh / generička greška ---------------------------------


def test_login_uspjeh_kreira_sesiju(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _make_user(session_factory, "sestra1", "lozinka123", UserRole.RECEPTION)

    response = _login(client, "sestra1", "lozinka123")

    assert response.status_code == 200
    body = response.json()
    assert body == {"username": "sestra1", "role": "RECEPTION"}
    assert SESSION_COOKIE_NAME in response.cookies
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header
    assert "Secure" in set_cookie_header
    assert "samesite=strict" in set_cookie_header.lower()


def test_login_pogresna_lozinka_i_nepostojeci_username_vracaju_identicnu_gresku(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _make_user(session_factory, "sestra1", "lozinka123", UserRole.RECEPTION)

    wrong_password = _login(client, "sestra1", "pogresna-lozinka")
    unknown_username = _login(client, "ne-postoji-uopste", "bilo-sta")

    assert wrong_password.status_code == 401
    assert unknown_username.status_code == 401
    assert wrong_password.json() == unknown_username.json()
    # Generička poruka ne smije spomenuti "korisničko ime" vs "lozinka" posebno
    # (ovdje provjeravamo da je poruka DOSLOVNO ista za oba slučaja — to je
    # suština zaštite od user enumeration, ne sadržaj same poruke).


def test_login_neaktivan_nalog_vraca_istu_gresku_kao_pogresna_lozinka(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        user = User(
            username="bivsi",
            password_hash=hash_password("lozinka123"),
            role=UserRole.RECEPTION,
            is_active=False,
        )
        session.add(user)
        session.commit()

    response = _login(client, "bivsi", "lozinka123")
    assert response.status_code == 401


def test_login_bez_kredencijala_vraca_422(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "", "password": ""})
    assert response.status_code == 422


# --- RBAC: neautentifikovan poziv -> 401 -------------------------------


def test_neautentifikovan_get_pending_vraca_401(client: TestClient) -> None:
    response = client.get("/api/booking-requests")
    assert response.status_code == 401


def test_neautentifikovan_confirm_vraca_401(client: TestClient) -> None:
    response = client.post(
        "/api/booking-requests/1/confirm",
        json={"doctor_id": 1, "service_id": 1, "start_time": "2026-08-20T09:00:00+00:00"},
    )
    assert response.status_code == 401


def test_neautentifikovan_reject_vraca_401(client: TestClient) -> None:
    response = client.post("/api/booking-requests/1/reject")
    assert response.status_code == 401


# --- RBAC: pogrešna uloga -> 403 (DENTIST i ADMIN eksplicitno) ---------


def test_dentist_ne_prolazi_na_confirm_vraca_403(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _make_user(session_factory, "dr.ana", "lozinka123", UserRole.DENTIST)
    _login(client, "dr.ana", "lozinka123")

    response = client.post(
        "/api/booking-requests/1/confirm",
        json={"doctor_id": 1, "service_id": 1, "start_time": "2026-08-20T09:00:00+00:00"},
    )
    assert response.status_code == 403


def test_admin_ne_prolazi_na_confirm_vraca_403(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """v3.1: ADMIN NE dobija automatski privilegije van administracije sistema
    — eksplicitno provjeravamo da nema slučajnog "ADMIN uvijek prolazi" bypass-a."""
    _make_user(session_factory, "admin1", "lozinka123", UserRole.ADMIN)
    _login(client, "admin1", "lozinka123")

    response = client.post(
        "/api/booking-requests/1/confirm",
        json={"doctor_id": 1, "service_id": 1, "start_time": "2026-08-20T09:00:00+00:00"},
    )
    assert response.status_code == 403


def test_admin_ne_prolazi_na_reject_vraca_403(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _make_user(session_factory, "admin1", "lozinka123", UserRole.ADMIN)
    _login(client, "admin1", "lozinka123")

    response = client.post("/api/booking-requests/1/reject")
    assert response.status_code == 403


def test_admin_ne_prolazi_na_get_pending_vraca_403(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _make_user(session_factory, "admin1", "lozinka123", UserRole.ADMIN)
    _login(client, "admin1", "lozinka123")

    response = client.get("/api/booking-requests")
    assert response.status_code == 403


# --- RBAC: RECEPTION uspješno prolazi kroz sva tri ---------------------


def test_reception_prolazi_kroz_get_pending(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _make_user(session_factory, "sestra1", "lozinka123", UserRole.RECEPTION)
    _login(client, "sestra1", "lozinka123")

    response = client.get("/api/booking-requests")
    assert response.status_code == 200
    assert response.json() == []


def test_reception_prolazi_kroz_confirm_i_reject(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    from dentaland.models import Doctor, Service

    with session_factory() as session:
        doctor = Doctor(ime="Ljubo")
        service = Service(naziv="Kontrola", trajanje_min=30, buffer_min=0)
        session.add_all([doctor, service])
        session.commit()
        doctor_id, service_id = doctor.id, service.id

    _make_user(session_factory, "sestra1", "lozinka123", UserRole.RECEPTION)
    _login(client, "sestra1", "lozinka123")

    submit = client.post(
        "/api/booking-requests",
        json={"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"},
    )
    request_id_1 = submit.json()["id"]

    confirm_response = client.post(
        f"/api/booking-requests/{request_id_1}/confirm",
        json={
            "doctor_id": doctor_id,
            "service_id": service_id,
            "start_time": "2026-08-20T09:00:00+00:00",
        },
    )
    assert confirm_response.status_code == 204

    submit2 = client.post(
        "/api/booking-requests",
        json={"ime": "Ivan", "telefon": "062", "requested_date": "2026-08-21"},
    )
    request_id_2 = submit2.json()["id"]

    reject_response = client.post(f"/api/booking-requests/{request_id_2}/reject")
    assert reject_response.status_code == 204


# --- Logout invalidira sesiju ------------------------------------------


def test_logout_invalidira_sesiju(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _make_user(session_factory, "sestra1", "lozinka123", UserRole.RECEPTION)
    _login(client, "sestra1", "lozinka123")

    assert client.get("/api/booking-requests").status_code == 200

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    after_logout = client.get("/api/booking-requests")
    assert after_logout.status_code == 401


def test_rate_limit_na_logout_endpointu(client: TestClient) -> None:
    statuses = [client.post("/api/auth/logout").status_code for _ in range(11)]
    assert 429 in statuses, "11. logout zahtjev u minuti treba biti odbijen (limit 10/minute)"


# --- Rate limit na login, odvojen od booking-request limita ------------


def test_rate_limit_na_login_endpointu(client: TestClient) -> None:
    payload = {"username": "ne-postoji", "password": "bilo-sta"}
    statuses = [client.post("/api/auth/login", json=payload).status_code for _ in range(6)]
    assert 429 in statuses, "6. login pokušaj u minuti treba biti odbijen (limit 5/minute)"


def test_login_rate_limit_ne_dijeli_kvotu_sa_booking_request(client: TestClient) -> None:
    """v3.1: odvojeni limiti — trošenje login kvote ne smije uticati na
    booking-request kvotu (i obrnuto, provjereno posredno kroz to da
    booking-request i dalje radi normalno nakon što je login kvota potrošena)."""
    payload = {"username": "ne-postoji", "password": "bilo-sta"}
    for _ in range(5):
        client.post("/api/auth/login", json=payload)
    limited = client.post("/api/auth/login", json=payload)
    assert limited.status_code == 429

    booking_response = client.post(
        "/api/booking-requests",
        json={"ime": "Ana", "telefon": "061", "requested_date": "2026-08-20"},
    )
    assert booking_response.status_code == 201


# --- Promjena lozinke invalidira sve sesije -----------------------------


def test_promjena_lozinke_invalidira_sve_postojece_sesije(
    session_factory: sessionmaker[Session],
) -> None:
    user_id = _make_user(session_factory, "sestra1", "stara-lozinka", UserRole.RECEPTION)

    from dentaland.services.auth import change_password, create_session, validate_session

    session_a = create_session(session_factory, user_id)
    session_b = create_session(session_factory, user_id)

    assert validate_session(session_factory, session_a.token) is not None
    assert validate_session(session_factory, session_b.token) is not None

    change_password(session_factory, user_id, "nova-lozinka")

    assert validate_session(session_factory, session_a.token) is None
    assert validate_session(session_factory, session_b.token) is None


def test_promjena_lozinke_je_atomska_sa_opozivom_sesija(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex review F1 (DENT-IMPROVE-013): ranija implementacija je koristila
    dvije odvojene transakcije (commit hash-a, pa zaseban commit opoziva
    sesija) — kvar u drugom koraku bi ostavio novu lozinku upisanu dok bi
    stare sesije ostale validne. Simuliramo TAČNO taj kvar (izuzetak nakon
    što je `password_hash` postavljen na objektu, prije `commit()`) i
    potvrđujemo da je CIJELA transakcija rollback-ovana — ni lozinka ni
    opoziv sesija nisu upisani, ne samo dio."""
    import dentaland.services.auth as auth_module
    from dentaland.services.auth import (
        AuthenticationError,
        authenticate_user,
        change_password,
        create_session,
        validate_session,
    )

    user_id = _make_user(session_factory, "sestra1", "stara-lozinka", UserRole.RECEPTION)
    session_a = create_session(session_factory, user_id)

    def _boom(session: Session, uid: int) -> None:
        raise RuntimeError("simuliran kvar tokom opoziva sesija")

    monkeypatch.setattr(auth_module, "_revoke_active_sessions", _boom)

    with pytest.raises(RuntimeError):
        change_password(session_factory, user_id, "nova-lozinka")

    # Stara sesija MORA ostati validna -- opoziv nikad nije commit-ovan.
    assert validate_session(session_factory, session_a.token) is not None
    # Stara lozinka MORA i dalje raditi -- hash promjena nikad nije
    # commit-ovana (rollback cijele transakcije, ne samo pola).
    authenticated = authenticate_user(session_factory, "sestra1", "stara-lozinka")
    assert authenticated.username == "sestra1"
    with pytest.raises(AuthenticationError):
        authenticate_user(session_factory, "sestra1", "nova-lozinka")


def test_invalidate_all_sessions_helper_je_idempotentan(
    session_factory: sessionmaker[Session],
) -> None:
    user_id = _make_user(session_factory, "sestra1", "lozinka123", UserRole.RECEPTION)
    # Poziv bez ijedne sesije ne smije dići grešku.
    invalidate_all_sessions_for_user(session_factory, user_id)


# --- Spot-check: lozinka/token se nikad ne pojavljuju u response/logu --


def test_login_response_ne_sadrzi_lozinku_ni_token(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _make_user(session_factory, "sestra1", "tajna-lozinka-xyz", UserRole.RECEPTION)

    response = _login(client, "sestra1", "tajna-lozinka-xyz")

    raw_body = response.text
    assert "tajna-lozinka-xyz" not in raw_body
    # Response body ne smije sadržati sirovi token (samo cookie ga nosi,
    # a to je poseban header, ne JSON tijelo).
    cookie_token = response.cookies.get(SESSION_COOKIE_NAME)
    assert cookie_token is not None
    assert cookie_token not in raw_body


def test_login_pokusaji_se_loguju_bez_lozinke(
    client: TestClient,
    session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _make_user(session_factory, "sestra1", "tajna-lozinka-xyz", UserRole.RECEPTION)

    with caplog.at_level(logging.INFO, logger="dentaland.auth"):
        _login(client, "sestra1", "tajna-lozinka-xyz")
        _login(client, "sestra1", "pogresna-lozinka")

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "LOGIN_SUCCESS" in log_text
    assert "LOGIN_FAILURE" in log_text
    assert "tajna-lozinka-xyz" not in log_text
    assert "pogresna-lozinka" not in log_text
