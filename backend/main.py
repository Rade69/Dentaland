"""Lokalni FastAPI backend za javne zahtjeve sa web forme (DENT-007).

Radi na ``localhost``, nad istom SQLite bazom koju koristi desktop
aplikacija — nema javnog hostinga. NEMA tokena za cancel/reschedule link —
eksplicitno van obima ovog zadatka, gated istim otvorenim pravnim
pitanjima.

Autentifikacija/RBAC (DENT-IMPROVE-013): tri staff-only endpointa
(``GET /api/booking-requests``, ``.../confirm``, ``.../reject``) zahtijevaju
``RECEPTION`` ulogu preko cookie-based sesije (vidi ``get_current_user``/
``require_role`` ispod i ``src/dentaland/services/auth.py``). Javni
``POST /api/booking-requests`` ostaje neautentifikovan (namjerno — to je
javna forma). HTTPS je deployment preduslov (v3.1) — lokalni dev/test rad
je i dalje HTTP, `Secure` cookie se u toj konfiguraciji ne šalje nazad na
plain HTTP (osim u testovima koji forsiraju `https://` scheme kroz
`TestClient(base_url=...)`, vidi `tests/test_auth.py`).

Pokretanje lokalno: ``uvicorn backend.main:app --reload``
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.reminder_scheduler import run_reminder_scheduler
from dentaland.models import Base
from dentaland.services.auth import (
    AuthenticatedUser,
    AuthenticationError,
    authenticate_user,
    create_session,
    invalidate_session,
    validate_session,
)
from dentaland.services.availability import OverlapError
from dentaland.services.notifications import send_booking_confirmation
from dentaland.services.requests import (
    RequestNotFoundError,
    confirm_request,
    create_request,
    list_pending,
    reject_request,
)

SESSION_COOKIE_NAME = "dentaland_session"

_session_factory_cache: sessionmaker[Session] | None = None


def _build_session_factory(db_url: str) -> sessionmaker[Session]:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def get_session_factory() -> sessionmaker[Session]:
    """FastAPI dependency — testovi je zamjenjuju preko `app.dependency_overrides`.

    ``DATABASE_URL`` (DENT-IMPROVE-012) ima prednost kad je postavljen —
    omogućava rad nad PostgreSQL. Bez nje, ponašanje je nepromijenjeno:
    SQLite fajl iz ``DENTALAND_DB_PATH`` (Faza 0 desktop default).
    """
    global _session_factory_cache
    if _session_factory_cache is None:
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            db_url = database_url
        else:
            db_path = os.environ.get("DENTALAND_DB_PATH", "dentaland.db")
            db_url = f"sqlite:///{db_path}"
        _session_factory_cache = _build_session_factory(db_url)
    return _session_factory_cache


limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    """Pokreni i uredno zaustavi in-process reminder scheduler."""
    factory_provider = app_instance.dependency_overrides.get(
        get_session_factory, get_session_factory
    )
    scheduler_task = asyncio.create_task(run_reminder_scheduler(factory_provider()))
    try:
        yield
    finally:
        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task


app = FastAPI(title="Dentaland — javni zahtjevi (lokalno)", lifespan=lifespan)
app.state.limiter = limiter
# slowapi-ov handler tip se ne poklapa tačno sa Starlette-ovim generičkim
# potpisom u novijim verzijama (poznato trvenje između biblioteka, ne greška
# u ovom kodu) — runtime ponašanje je testirano i tačno (vidi
# test_rate_limit_na_submit_endpointu).
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]


def get_current_user(request: Request, session_factory: SessionFactoryDep) -> AuthenticatedUser:
    """FastAPI dependency — 401 ako nema sesionog kolačića ili je nevažeći/istekao."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=401, detail="nije autentifikovano")
    user = validate_session(session_factory, token)
    if user is None:
        raise HTTPException(status_code=401, detail="nevažeća ili istekla sesija")
    return user


CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_role(allowed_roles: list[str]) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """Vrati FastAPI dependency koja propušta samo navedene uloge (403 inače).

    UI skrivanje nije sigurnosna kontrola (v3.1) — ova provjera je jedini
    stvarni gate, na nivou endpointa. NIJEDNA uloga ne prolazi "automatski"
    (npr. ADMIN NE zaobilazi ovu listu) — provjera je uvijek eksplicitna
    članstvo-u-listi provjera, namjerno bez posebnog slučaja za bilo koju
    ulogu.
    """

    def _require_role(current_user: CurrentUserDep) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="nedovoljna ovlaštenja")
        return current_user

    return _require_role


# RECEPTION-only gate za tri postojeća staff endpointa (DENT-IMPROVE-013) —
# definisan JEDNOM, primijenjen na sva tri ispod (ista logika, jedan poziv
# `require_role`, ne duplirana lista uloga na svakom endpointu).
RequireReceptionDep = Annotated[AuthenticatedUser, Depends(require_role(["RECEPTION"]))]

# Lokalno testiranje samo — web/ se otvara sa file:// ili drugog localhost
# porta, pa treba CORS. MORA se suziti na stvaran origin prije javnog rada.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class BookingRequestIn(BaseModel):
    ime: str = Field(min_length=1, max_length=200)
    telefon: str = Field(min_length=1, max_length=50)
    email: str = ""
    requested_date: date


class BookingRequestOut(BaseModel):
    id: int
    status: str = "PENDING"


class PendingRequestOut(BaseModel):
    id: int
    ime: str
    telefon: str
    email: str
    requested_date: date
    created_at: datetime


class ConfirmIn(BaseModel):
    doctor_id: int
    service_id: int
    start_time: datetime


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginOut(BaseModel):
    username: str
    role: str


@app.post("/api/auth/login", response_model=LoginOut)
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    payload: LoginIn,
    session_factory: SessionFactoryDep,
) -> LoginOut:
    """Sopstveni rate limit (5/minute), odvojen od `/api/booking-requests`
    (10/minute) — v3.1 eksplicitno traži odvojene limite (slowapi prati
    kvotu po ruti, ne globalno, pa isti `limiter` objekat ovdje daje
    nezavisnu kvotu).

    Generička greška (401, ista poruka) na pogrešno korisničko ime ILI
    pogrešnu lozinku — `authenticate_user` ne otkriva koji je slučaj.

    `source_ip` (DENT-IMPROVE-014B) dolazi iz stvarnog `Request` objekta —
    dostupan samo ovdje, ne u `auth.py` — i prosljeđuje se u
    `authenticate_user` da se upiše u `LOGIN_SUCCESS`/`LOGIN_FAILURE`
    audit zapis. `request.client` može biti `None` (npr. neki test/proxy
    konteksti) — u tom slučaju `source_ip` ostaje `NULL`, ne diže grešku.
    """
    source_ip = request.client.host if request.client is not None else None
    try:
        user = authenticate_user(
            session_factory, payload.username, payload.password, source_ip=source_ip
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    session_dto = create_session(session_factory, user.id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_dto.token,
        httponly=True,
        secure=True,
        samesite="strict",
        expires=session_dto.expires_at,
    )
    return LoginOut(username=user.username, role=user.role)


@app.post("/api/auth/logout", status_code=204)
@limiter.limit("10/minute")
def logout(request: Request, response: Response, session_factory: SessionFactoryDep) -> None:
    """Invalidira trenutnu sesiju (ako postoji) i briše kolačić."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is not None:
        invalidate_session(session_factory, token)
    response.delete_cookie(SESSION_COOKIE_NAME)


@app.post("/api/booking-requests", response_model=BookingRequestOut, status_code=201)
@limiter.limit("10/minute")
def submit_booking_request(
    request: Request,
    payload: BookingRequestIn,
    session_factory: SessionFactoryDep,
) -> BookingRequestOut:
    dto = create_request(
        session_factory, payload.ime, payload.telefon, payload.email, payload.requested_date
    )
    # Best-effort: email potvrda ne smije srušiti booking tok (funkcija ne diže).
    send_booking_confirmation(payload.email, payload.requested_date)
    return BookingRequestOut(id=dto.id)


@app.get("/api/booking-requests", response_model=list[PendingRequestOut])
@limiter.limit("30/minute")
def get_pending_requests(
    request: Request,
    session_factory: SessionFactoryDep,
    _current_user: RequireReceptionDep,
) -> list[PendingRequestOut]:
    return [
        PendingRequestOut(
            id=r.id,
            ime=r.ime,
            telefon=r.telefon,
            email=r.email,
            requested_date=r.requested_date,
            created_at=r.created_at,
        )
        for r in list_pending(session_factory)
    ]


@app.post("/api/booking-requests/{request_id}/confirm", status_code=204)
@limiter.limit("20/minute")
def confirm(
    request: Request,
    request_id: int,
    payload: ConfirmIn,
    session_factory: SessionFactoryDep,
    _current_user: RequireReceptionDep,
) -> None:
    try:
        confirm_request(
            session_factory,
            request_id,
            payload.doctor_id,
            payload.service_id,
            payload.start_time,
        )
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OverlapError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/booking-requests/{request_id}/reject", status_code=204)
@limiter.limit("20/minute")
def reject(
    request: Request,
    request_id: int,
    session_factory: SessionFactoryDep,
    _current_user: RequireReceptionDep,
) -> None:
    try:
        reject_request(session_factory, request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
