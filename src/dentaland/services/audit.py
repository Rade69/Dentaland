"""Servisni sloj za append-only audit log (DENT-IMPROVE-014).

**Jezgro — bez instrumentacije stvarnih poziva.** Ovaj modul isporučuje
samo `write_audit_event(...)`. Instrumentacija stvarnih mjesta gdje se
audit događaji dešavaju (login, izmjene termina) radi se u dva odvojena,
paralelna, buduća zadatka nakon merge-a ovog jezgra:

- `DENT-IMPROVE-014B` — `LOGIN_SUCCESS`/`LOGIN_FAILURE` iz
  `src/dentaland/services/auth.py` / `backend/main.py` login route
  handlera.
- `DENT-IMPROVE-014C` — `CREATE/UPDATE/CANCEL/DELETE_APPOINTMENT` iz
  `src/dentaland/services/appointments.py`.

**Append-only napomena** (v3.1 princip #7 — audit promjene zahtijevaju
dva nezavisna reviewera): ovaj modul NAMJERNO ne izlaže
`update_audit_event`/`delete_audit_event` niti bilo koju drugu funkciju
koja mijenja/briše postojeći red. Append-only ponašanje se u ovom obimu
postiže disciplinom servisnog sloja (samo insert je izložen), ne DB-nivo
trigerom/permisijom — proporcionalno veličini projekta (jedan VPS, jedna
ordinacija), vidi `CLAUDE.md` "Šta se namjerno ne gradi unaprijed". Ovo je
svjesna, dokumentovana odluka, ne propust.

**API dizajn — `session` vs `session_factory`:** `write_audit_event`
prihvata obavezan `session_factory` I opcioni keyword-only `session`
parametar (isti obrazac kao `_revoke_active_sessions` helper u
`src/dentaland/services/auth.py`, prilagođen da bude javni jer ga budući
cross-modul pozivalac — DENT-IMPROVE-014C — mora moći pozvati direktno):

- Kad pozivalac već ima otvorenu sesiju/transakciju (npr. 014C upisuje
  audit red kao dio iste transakcije koja mijenja termin — atomičnost:
  ili oboje uspije, ili ništa), proslijedi `session=` — funkcija radi
  `session.add(...)` i NE commit-uje; pozivalac kontroliše commit granicu.
- Kad pozivalac nema okolnu transakciju (samostalna upotreba, npr. 014B
  login audit poziv iz route handlera), ne prosljeđuje `session` —
  funkcija otvara svoju `with session_factory() as session:`, radi
  `session.add(...)` i sama commit-uje.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from dentaland.models import AuditAction, AuditEvent


def _add_audit_event(
    session: OrmSession,
    action: AuditAction,
    *,
    actor_user_id: int | None,
    resource_type: str | None,
    resource_id: int | None,
    request_id: str | None,
    source_ip: str | None,
    metadata: dict[str, Any] | None,
) -> None:
    """Dodaj `AuditEvent` u POSTOJEĆU sesiju — ne commit-uje.

    Privatni helper, dijeli logiku serijalizacije `metadata` između
    in-session i samostalne putanje u `write_audit_event`."""
    metadata_minimal = json.dumps(metadata) if metadata is not None else None
    session.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            source_ip=source_ip,
            metadata_minimal=metadata_minimal,
        )
    )


def write_audit_event(
    session_factory: Callable[[], OrmSession],
    action: AuditAction,
    *,
    actor_user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    request_id: str | None = None,
    source_ip: str | None = None,
    metadata: dict[str, Any] | None = None,
    session: OrmSession | None = None,
) -> None:
    """Upiši append-only audit zapis.

    Čist insert, nikad update/delete postojećeg reda (vidi docstring
    modula). Pozivalac je ISKLJUČIVO odgovoran da `metadata` nikad ne
    sadrži lozinku/token/medicinski sadržaj/pun request body (v3.1: "audit
    log ne kopira medicinski sadržaj u metadata") — ova funkcija ne
    validira niti sanitizuje sadržaj `metadata`.

    Args:
        session_factory: Factory za novu sesiju — korišten SAMO ako
            `session` nije prosljeđen (samostalna upotreba, funkcija
            otvara i commit-uje svoju transakciju).
        action: Jedna od 7 `AuditAction` vrijednosti.
        actor_user_id: Nullable — `NULL` za desktop-porijeklo pozive (nema
            koncept ulogovanog korisnika) i za `LOGIN_FAILURE` (user
            enumeration zaštita i na audit nivou).
        resource_type: Nullable, npr. `"appointment"`, `"user"`.
        resource_id: Nullable, ID pogođenog resursa.
        request_id: Nullable — backend popunjava, desktop uvijek `NULL`.
        source_ip: Nullable — backend popunjava iz `Request`, desktop
            uvijek `NULL`.
        metadata: Nullable dict, JSON-enkodiran u `metadata_minimal` —
            NIKAD lozinka/token/medicinski sadržaj/PII van onoga što je već
            u `resource_type`/`resource_id`.
        session: Opciona već-otvorena sesija/transakcija. Kad je
            prosljeđena, upis ide UNUTAR nje (`session.add`, BEZ
            `commit()`) — omogućava pozivaocu (npr. DENT-IMPROVE-014C) da
            kombinuje audit upis sa svojom sopstvenom transakcijom, tako
            da audit zapis i prateća izmjena uspiju ili propadnu zajedno
            (atomičnost). Kad NIJE prosljeđena, funkcija otvara i
            commit-uje sopstvenu sesiju preko `session_factory`
            (samostalna upotreba, npr. DENT-IMPROVE-014B login audit poziv
            bez okolne transakcije).
    """
    if session is not None:
        _add_audit_event(
            session,
            action,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            source_ip=source_ip,
            metadata=metadata,
        )
        return

    with session_factory() as new_session:
        _add_audit_event(
            new_session,
            action,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            source_ip=source_ip,
            metadata=metadata,
        )
        new_session.commit()
