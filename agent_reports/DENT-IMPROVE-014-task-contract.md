---
task_id: DENT-IMPROVE-014
risk: HIGH
implementer: claude
reviewers: [codex, pi]
status: "DONE (jezgro) — MERGED u main (merge commit 41cb94e, 27.8.2026). AuditEvent model + AuditAction enum (v3.1 šema, 9 polja), write_audit_event servisna funkcija sa opcionim session= za atomsku upotrebu. Nula instrumentacije stvarnih poziva — to rade DENT-IMPROVE-014B/014C. Review: Codex+Pi (PASS_WITH_NOTES). Radovan human approval 27.8.2026."
created_at: 2026-08-27
---

# DENT-IMPROVE-014 — Append-only audit log (jezgro)

## Kontekst

`docs/DENTALAND_IMPROVEMENT_BACKLOG.md` sekcija 15 — HIGH, compliance/
security, sad jedini neblokiran Prioritet C task (`DENT-IMPROVE-013` DONE,
merge `da67027`, 27.8.2026). `DENT-IMPROVE-015` (production gate) čeka
ovaj task.

**Ovo je JEZGRO, jedan od tri povezana taska.** Nakon što se OVAJ task
mergne u `main`, dva NEZAVISNA, PARALELNA taska instrumentišu stvarna
mjesta gdje se audit događaji dešavaju:
- `DENT-IMPROVE-014B` (implementer Pi) — LOGIN_SUCCESS/LOGIN_FAILURE.
- `DENT-IMPROVE-014C` (implementer Crush) — CREATE/UPDATE/CANCEL/DELETE_APPOINTMENT.

**014B i 014C NE MOGU početi prije nego se OVAJ task mergne** — oba
uvoze `AuditEvent` model i `write_audit_event` funkciju koje ovaj task
kreira. Nula preklapanja fajlova između 014B i 014C (potvrđeno prije
pisanja svih kontrakata) — pravi paralelizam nakon ove sekvence.

**Izvor istine za tehničku šemu:**
`docs/dentaland-razvojni-plan-v3.1.md`, sekcija "Audit log" (oko linije
267):

```text
audit_events
- id, actor_user_id, action, resource_type, resource_id,
  occurred_at, request_id, source_ip (uz retention), metadata_minimal
```

> Akcije: LOGIN_SUCCESS/FAILURE, VIEW_PATIENT, CREATE/UPDATE/CANCEL_APPOINTMENT,
> EXPORT_PERSONAL_DATA, DELETE_OR_ANONYMIZE_PERSONAL_DATA, CHANGE_ROLE,
> VIEW_MEDICAL_DATA. Audit log ne kopira medicinski sadržaj u `metadata`.

## Bitno arhitektonsko ograničenje (Radovanova odluka, 27.8.2026)

**Desktop app (Faza 0) nema NIKAKAV koncept ulogovanog korisnika** —
potvrđeno grep-om, nema `current_user`/`session`/auth koncepta bilo gdje
u `desktop/`. Pošto se CREATE/UPDATE/CANCEL/DELETE_APPOINTMENT skoro
isključivo dešavaju iz desktopa (preko `AppointmentService` fasade →
`src/dentaland/services/appointments.py`), ti audit zapisi će imati
`actor_user_id = NULL`. Radovan je potvrdio: **prihvatiti NULL za sada,
dokumentovati kao poznato ograničenje — ne graditi desktop login/"ko je
za kompjuterom" izbor u ovom tasku** (bio bi mnogo veći, poseban
zadatak). Samo `LOGIN_SUCCESS`/`LOGIN_FAILURE` (iz `DENT-IMPROVE-013`
backend auth-a) imaju pravi `actor_user_id`.

## Trenutno stanje repoa (provjereno 27.8.2026)

- `src/dentaland/services/appointments.py` sadrži `create_appointment`,
  `update_appointment`, `cancel_appointment`, `delete_appointment` —
  JEDINA zajednička tačka kroz koju i desktop (`AppointmentService` fasada
  u `booking.py`) rade sve izmjene termina. Ne dirati ove funkcije u OVOM
  tasku (to je `DENT-IMPROVE-014C`).
- `src/dentaland/services/auth.py` (`DENT-IMPROVE-013`) već ima
  `logger.info("LOGIN_SUCCESS"/"LOGIN_FAILURE", ...)` pozive — ostaju
  netaknuti u ovom tasku (to je `DENT-IMPROVE-014B`).
- Nema nikakvog `AuditEvent`/`audit_events` modela trenutno.
- Nema `CHANGE_ROLE` akcije/endpointa bilo gdje u kodu — `scripts/create_user.py`
  samo kreira nalog sa ulogom pri kreiranju, nema "promijeni ulogu"
  funkcionalnosti. Enum vrijednost se definiše (v3.1 kompletnost, buduća
  kompatibilnost), ali nema trenutnog pozivaoca — isti tretman kao EXCLUDE
  constraint u `DENT-IMPROVE-012` (definisano, namjerno dormant, ne
  graditi UI/endpoint za njega u ovom tasku).
- `VIEW_PATIENT`, `EXPORT_PERSONAL_DATA`, `DELETE_OR_ANONYMIZE_PERSONAL_DATA`,
  `VIEW_MEDICAL_DATA` iz v3.1-ove pune liste **NISU** u obimu — nemaju
  odgovarajuću izgrađenu funkcionalnost (nema "pregled pacijenta" ekrana,
  nema medical data koncepta, nema GDPR export/anonimizacija flow-a još).
  Backlog "Minimum events" lista (uža, autoritativna za OVAJ task) ih ne
  sadrži.
- Alembic head: `e5f6a7b8c9d0` (provjeri ponovo sa `alembic heads` prije
  pisanja migracije — mogao se promijeniti).

## Cilj

`AuditEvent` model (tačna v3.1 šema) + Alembic migracija +
`src/dentaland/services/audit.py` sa `write_audit_event(...)` funkcijom —
**bez instrumentacije stvarnih poziva** (to rade 014B/014C paralelno,
nakon merge-a).

## Required scope

1. **`src/dentaland/models.py`** — novi `AuditEvent` model:
   - `id` (PK, autoincrement)
   - `actor_user_id` (nullable FK → `users.id` — NULL dozvoljen, vidi
     arhitektonsko ograničenje gore)
   - `action` (`Enum(AuditAction, native_enum=False)` — isti obrazac kao
     `AppointmentStatus`/`UserRole`; vrijednosti: `LOGIN_SUCCESS`,
     `LOGIN_FAILURE`, `CREATE_APPOINTMENT`, `UPDATE_APPOINTMENT`,
     `CANCEL_APPOINTMENT`, `DELETE_APPOINTMENT`, `CHANGE_ROLE` — tačno
     backlog "Minimum events" lista, ne šira v3.1 lista)
   - `resource_type` (nullable `String`, npr. `"appointment"`, `"user"`)
   - `resource_id` (nullable `Integer`)
   - `occurred_at` (`TZDateTime`, default `utcnow()` — isti obrazac kao
     postojeći modeli)
   - `request_id` (nullable `String` — backend popunjava, desktop uvijek
     `NULL`)
   - `source_ip` (nullable `String` — backend popunjava iz `Request`,
     desktop uvijek `NULL`)
   - `metadata_minimal` (nullable `Text` — mali JSON-enkodiran string;
     **pozivalac je odgovoran da nikad ne stavi lozinku/token/medicinski
     sadržaj/pun request body ovdje** — dokumentovati ovo eksplicitno u
     docstringu modela, v3.1 zahtjev)
2. **`src/dentaland/services/audit.py`** (novo):
   - `write_audit_event(session_factory, action, *, actor_user_id=None, resource_type=None, resource_id=None, request_id=None, source_ip=None, metadata=None) -> None`
     — čist insert, jedan `commit()`.
   - **Namjerno NEMA `update_audit_event`/`delete_audit_event` funkcije
     nigdje u servisnom sloju** — "append-only" se u ovom obimu postiže
     disciplinom (ne izlagati mutacioni API), ne DB-nivo trigerom/permisijom
     (proporcionalno veličini projekta). Dokumentovati ovu odluku u
     docstringu/izvještaju eksplicitno, ne prećutno izostaviti.
3. **Alembic migracija** (novo, `down_revision` = trenutni head — provjeri
   sam) — kreira `audit_events` tabelu.
4. **Testovi** (`tests/test_audit.py`, novo):
   - `write_audit_event` upisuje red sa svim poljima ispravno.
   - Sva nullable polja (`actor_user_id`, `resource_id`, `request_id`,
     `source_ip`, `metadata_minimal`) prihvataju `None`.
   - Svih 7 `AuditAction` vrijednosti se mogu upisati.
   - Uzastopni pozivi ne mijenjaju/ne brišu prethodne redove (append-only
     ponašanje na nivou funkcije).

## Critical constraints

- **Ne instrumentisati stvarne pozive** (`auth.py`, `appointments.py`,
  `backend/main.py`) — to je van obima OVOG taska, radi se u 014B/014C.
- **Ne graditi `VIEW_PATIENT`/`EXPORT_PERSONAL_DATA`/
  `DELETE_OR_ANONYMIZE_PERSONAL_DATA`/`VIEW_MEDICAL_DATA`** — nemaju
  odgovarajuću funkcionalnost, van obima.
- **Ne graditi CHANGE_ROLE endpoint/UI** — samo enum vrijednost,
  dormant.
- **Ne graditi retention/brisanje job** — v3.1 pominje "uz retention" ali
  backlog acceptance za ovaj task to ne traži eksplicitno; ako se odluči
  da treba, to je `OUT_OF_SCOPE_FINDING` za buduću odluku, ne tiho dodati.
- **Nikad ne pisati lozinku/token/medicinski sadržaj u `metadata_minimal`**
  — dokumentovano u modelu, provjereno testom da servisna funkcija ne
  validira/ne sanitizuje sadržaj sama (odgovornost je na pozivaocu, po
  dizajnu — dokumentovati zašto).

## Acceptance criteria

- [ ] `AuditEvent` model postoji sa tačnim v3.1 poljima
- [ ] Migracija radi čisto (`alembic upgrade head`/`downgrade -1`)
- [ ] `write_audit_event` upisuje sve navedene scenarije ispravno
- [ ] Nema `update`/`delete` funkcije za audit zapise u servisnom sloju
- [ ] Postojeći `pytest tests/ -q`, `ruff`, `mypy`, `agent_sensors.py --all`
      ostaju čisti
- [ ] `src/dentaland/services/appointments.py`, `auth.py`, `backend/main.py`,
      `desktop/**` netaknuti (nula instrumentacije u ovom tasku)

## Allowed paths

```text
src/dentaland/models.py                  (SAMO dodati AuditEvent/AuditAction)
src/dentaland/services/audit.py          (novo)
migrations/versions/*.py                 (SAMO nova migracija)
tests/test_audit.py                      (novo)
agent_reports/**
docs/DENTALAND_IMPROVEMENT_BACKLOG.md    (samo status napomena)
```

## Forbidden paths

```text
src/dentaland/services/appointments.py   (DENT-IMPROVE-014C posao)
src/dentaland/services/auth.py           (DENT-IMPROVE-014B posao)
backend/main.py
desktop/**
web/**
migrations/versions/**                   (postojeći fajlovi, osim nove migracije)
migrations/env.py
alembic.ini
```

## Review

Standardan HIGH proces (v3.1 princip #7: audit promjene zahtijevaju dva
nezavisna reviewera). Codex (Reviewer 1, obavezan) + Pi (Reviewer 2).
Implementer Claude (shema/migracija, `CLAUDE.md`).

Reviewer posebno provjerava:
- Da šema tačno prati v3.1 (svih 9 polja, nullable gdje treba).
- Da servisni sloj STVARNO ne izlaže mutacioni API za audit zapise.
- Da nijedan poziv u `appointments.py`/`auth.py`/`backend/main.py` nije
  slučajno dodat (provjera da je ovo stvarno samo jezgro, ne
  preduhitrena instrumentacija).

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-014 --agent claude --paths src/dentaland/models.py,src/dentaland/services/audit.py
```

Nakon merge-a u `main`, `DENT-IMPROVE-014B` i `DENT-IMPROVE-014C` claimuju
svoje odvojene putanje i mogu ići paralelno (vidi njihove kontrakte).

## Plan prije izmjene (HIGH — obavezno)

Kratak plan u `agent_reports/` prije prve izmjene koda, isti obrazac kao
`DENT-IMPROVE-012`/`013`.
