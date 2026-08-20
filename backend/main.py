"""Lokalni FastAPI backend za javne zahtjeve sa web forme (DENT-007).

Radi na ``localhost``, nad istom SQLite bazom koju koristi desktop
aplikacija — nema javnog hostinga. NEMA autentifikacije (RBAC nije još
izgrađen) — prihvatljivo dok je striktno lokalno, MORA se riješiti prije
bilo kakvog javnog izlaganja (vidi ``CLAUDE.md`` "Otvorena pitanja"). NEMA
tokena za cancel/reschedule link — eksplicitno van obima ovog zadatka,
gated istim otvorenim pravnim pitanjima.

Pokretanje lokalno: ``uvicorn backend.main:app --reload``
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.reminder_scheduler import run_reminder_scheduler
from dentaland.models import Base
from dentaland.services.notifications import send_booking_confirmation
from dentaland.services.requests import (
    OverlapError,
    RequestNotFoundError,
    confirm_request,
    create_request,
    list_pending,
    reject_request,
)

_session_factory_cache: sessionmaker[Session] | None = None


def _build_session_factory(db_path: str) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def get_session_factory() -> sessionmaker[Session]:
    """FastAPI dependency — testovi je zamjenjuju preko `app.dependency_overrides`."""
    global _session_factory_cache
    if _session_factory_cache is None:
        db_path = os.environ.get("DENTALAND_DB_PATH", "dentaland.db")
        _session_factory_cache = _build_session_factory(db_path)
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
def get_pending_requests(session_factory: SessionFactoryDep) -> list[PendingRequestOut]:
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
def confirm(
    request_id: int,
    payload: ConfirmIn,
    session_factory: SessionFactoryDep,
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
def reject(request_id: int, session_factory: SessionFactoryDep) -> None:
    try:
        reject_request(session_factory, request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
