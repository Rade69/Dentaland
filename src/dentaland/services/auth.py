"""Servisni sloj za autentifikaciju i sesije (DENT-IMPROVE-013).

Password hashing: Argon2id preko ``argon2-cffi`` (v3.1 eksplicitan
zahtjev — ne bcrypt/passlib default).

Session token: isti sigurni obrazac kao planirani cancel-link token
(``CLAUDE.md``) — ``secrets.token_urlsafe(32)`` sirov token (nikad upisan
u bazu), SHA-256 heks hash čuvan u ``sessions.token_hash``,
``hmac.compare_digest()`` za poređenje, ``expires_at`` + eksplicitna
invalidaciona semantika (``revoked_at``, ne brisanje reda).

``authenticate_user`` vraća generičku grešku bez obzira da li je
korisničko ime nepoznato ili je lozinka pogrešna (zaštita od user
enumeration) — i u oba slučaja izvršava Argon2 verifikaciju (na pravom
ili dummy hash-u) da vremenski profil bude što bliži identičan.

Audit granica (Radovanova odluka, kontrakt DENT-IMPROVE-013): login
pokušaji idu SAMO u standardni ``logging`` modul (username, ishod,
timestamp — NIKAD lozinka/token/cookie vrijednost). Prava append-only
audit tabela je poseban budući zadatak (DENT-IMPROVE-014) — logovanje je
namjerno koncentrisano na dva mjesta ispod (`authenticate_user`) da se
kasnije lako zamijeni/dopuni jednim audit pozivom.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from dentaland.models import Session as SessionModel
from dentaland.models import User, UserRole, utcnow

logger = logging.getLogger("dentaland.auth")

# Koliko sesija traje bez aktivnosti — nema "remember me"/refresh u ovom
# obimu (van scope-a), fiksan TTL od kreiranja.
SESSION_TTL = timedelta(hours=12)

_hasher = PasswordHasher()

# Dummy hash korišten kad korisničko ime ne postoji — Argon2 verifikacija
# se svejedno izvrši protiv njega da vremenski profil bude blizak
# stvarnom slučaju (ublažava, ne eliminiše potpuno, timing-based user
# enumeration; sama poruka/status kod su identični u oba slučaja).
_DUMMY_PASSWORD_HASH = _hasher.hash("dummy-lozinka-za-timing-zastitu")


class AuthenticationError(Exception):
    """Generička login greška — poruka NIKAD ne otkriva da li je problem
    korisničko ime ili lozinka."""


@dataclass(frozen=True)
class AuthenticatedUser:
    """Plain DTO — nikad se ne vraća sirovi ORM `User` van sesije servisa."""

    id: int
    username: str
    role: UserRole


@dataclass(frozen=True)
class SessionDTO:
    """Sirov token se vraća TAČNO JEDNOM, pri kreiranju — nikad se ne može
    ponovo dobiti iz baze (čuva se samo hash)."""

    token: str
    expires_at: datetime


def hash_password(password: str) -> str:
    """Argon2id hash lozinke."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Vrati True ako lozinka odgovara hash-u, inače False (nikad ne diže)."""
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False
    return True


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate_user(
    session_factory: Callable[[], OrmSession], username: str, password: str
) -> AuthenticatedUser:
    """Provjeri kredencijale. Diže `AuthenticationError` (generička poruka)
    na pogrešno korisničko ime ILI pogrešnu lozinku ILI neaktivan nalog —
    namjerno se ne razlikuje koji je slučaj u pitanju."""
    with session_factory() as session:
        user = session.scalar(select(User).where(User.username == username))

        if user is None or not user.is_active:
            # Izvrši verifikaciju i kad korisnik ne postoji (protiv dummy
            # hash-a) — drži vremenski profil blizak stvarnom slučaju.
            verify_password(_DUMMY_PASSWORD_HASH, password)
            logger.info("LOGIN_FAILURE username=%r", username)
            raise AuthenticationError("pogrešno korisničko ime ili lozinka")

        if not verify_password(user.password_hash, password):
            logger.info("LOGIN_FAILURE username=%r", username)
            raise AuthenticationError("pogrešno korisničko ime ili lozinka")

        logger.info("LOGIN_SUCCESS username=%r", username)
        return AuthenticatedUser(id=user.id, username=user.username, role=user.role)


def create_session(
    session_factory: Callable[[], OrmSession],
    user_id: int,
    *,
    ttl: timedelta = SESSION_TTL,
) -> SessionDTO:
    """Kreiraj novu sesiju za korisnika. Vraća sirov token (samo jednom)."""
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = utcnow() + ttl

    with session_factory() as session:
        session.add(
            SessionModel(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        session.commit()

    return SessionDTO(token=token, expires_at=expires_at)


def validate_session(
    session_factory: Callable[[], OrmSession], token: str
) -> AuthenticatedUser | None:
    """Vrati korisnika za validan, nerevocirani, neistekli token — inače None."""
    token_hash = _hash_token(token)

    with session_factory() as session:
        db_session = session.scalar(
            select(SessionModel).where(SessionModel.token_hash == token_hash)
        )
        if db_session is None:
            return None
        # Dodatna odbrana uz indeksiranu jednakost iznad — eksplicitna
        # constant-time provjera (v3.1/CLAUDE.md zahtjev: hmac.compare_digest,
        # nikad `==`, za poređenje sigurnosnih tokena).
        if not hmac.compare_digest(db_session.token_hash, token_hash):
            return None
        if db_session.revoked_at is not None:
            return None
        if db_session.expires_at <= utcnow():
            return None

        user = session.get(User, db_session.user_id)
        if user is None or not user.is_active:
            return None

        return AuthenticatedUser(id=user.id, username=user.username, role=user.role)


def invalidate_session(session_factory: Callable[[], OrmSession], token: str) -> None:
    """Invalidiraj (revoke) sesiju po sirovom tokenu — idempotentno, ne diže
    ako token ne postoji/već je revociran."""
    token_hash = _hash_token(token)

    with session_factory() as session:
        db_session = session.scalar(
            select(SessionModel).where(SessionModel.token_hash == token_hash)
        )
        if db_session is not None and db_session.revoked_at is None:
            db_session.revoked_at = utcnow()
            session.commit()


def _revoke_active_sessions(session: OrmSession, user_id: int) -> None:
    """Revoke sve aktivne (nerevocirane) sesije korisnika UNUTAR postojeće
    sesije/transakcije — ne commit-uje, pozivalac kontroliše commit granicu
    (vidi `invalidate_all_sessions_for_user` i `change_password`)."""
    active_sessions = session.scalars(
        select(SessionModel).where(
            SessionModel.user_id == user_id,
            SessionModel.revoked_at.is_(None),
        )
    ).all()
    now = utcnow()
    for db_session in active_sessions:
        db_session.revoked_at = now


def invalidate_all_sessions_for_user(
    session_factory: Callable[[], OrmSession], user_id: int
) -> None:
    """Revoke SVE aktivne (nerevocirane) sesije korisnika — v3.1 zahtjev:
    obavezno se poziva pri promjeni lozinke (vidi `change_password`)."""
    with session_factory() as session:
        _revoke_active_sessions(session, user_id)
        session.commit()


def change_password(
    session_factory: Callable[[], OrmSession], user_id: int, new_password: str
) -> None:
    """Postavi novu lozinku i invalidiraj SVE postojeće sesije korisnika,
    ATOMSKI (Codex review F1, DENT-IMPROVE-013): ranija verzija je koristila
    dvije odvojene transakcije/commit-e (hash pa opoziv sesija) — ako bi drugi
    korak pukao nakon prvog commita, nova lozinka bi bila upisana dok bi stare
    sesije ostale validne. Obje izmjene sad idu u JEDNOJ sesiji/transakciji sa
    jednim `commit()` — na bilo kojem izuzetku prije commit-a, cijela
    transakcija se rollback-uje (ništa nije upisano), ne samo dio nje.

    Nema endpoint za ovo u ovom zadatku — poziva je direktno
    `scripts/create_user.py` (buduća "promijeni lozinku" akcija) ili budući
    admin tok."""
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError(f"korisnik {user_id} ne postoji")
        user.password_hash = hash_password(new_password)
        _revoke_active_sessions(session, user_id)
        session.commit()
