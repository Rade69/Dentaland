---
task_id: DENT-IMPROVE-014
risk: HIGH
implementer: claude
reviewers: [codex, pi]
status: PLAN
created_at: 2026-08-27
---

# Plan — DENT-IMPROVE-014: Append-only audit log (jezgro)

## Cilj

`AuditEvent` model + `AuditAction` enum (tačna v3.1 šema, backlog "Minimum
events" 7 vrijednosti) + Alembic migracija + `src/dentaland/services/audit.py`
sa `write_audit_event(...)` funkcijom. **Bez instrumentacije stvarnih
poziva** — to rade `DENT-IMPROVE-014B` (Pi, login) i `DENT-IMPROVE-014C`
(Crush, appointments) paralelno, poslije merge-a ovog taska.

## Pogođeno

- `src/dentaland/models.py` — dodati `AuditAction` (enum) i `AuditEvent`
  (novi model), SAMO dodati, ne dirati `Appointment`/`User`/`Session`/itd.
- `src/dentaland/services/audit.py` (novo) — `write_audit_event(...)`.
- Nova Alembic migracija, `down_revision = e5f6a7b8c9d0` (potvrđen head sa
  `alembic heads` — vidi ispod).
- `tests/test_audit.py` (novo).

## Pročitano prije koda (obavezno po instrukciji)

Pročitao sam `DENT-IMPROVE-014B` i `DENT-IMPROVE-014C` kontrakte prije
pisanja ijedne linije koda:

- **014C zahtijeva atomičnost**: audit upis za CREATE/UPDATE/CANCEL/
  DELETE_APPOINTMENT mora biti u ISTOJ transakciji/commit-u kao izmjena
  termina (isti princip kao `change_password` iz DENT-IMPROVE-013 Fix
  runda 1). Ako `write_audit_event` sama otvara `with session_factory()
  as session:` i sama commit-uje, 014C to ne može postići bez
  dupliciranja logike.
- **014B nema sopstvenu okolnu transakciju** oko login logike u tom
  smislu — `authenticate_user` već radi sve unutar jedne `with
  session_factory()` sesije, ali `write_audit_event` poziv za login se
  najvjerovatnije dešava POSLIJE `authenticate_user` vraća (npr. u
  `backend/main.py` login route handleru, gdje treba i `source_ip` iz
  `Request` objekta) — samostalna upotreba je prihvatljiva tu.

**Dizajn odluka**: `write_audit_event` prima OBAVEZAN `session_factory:
Callable[[], OrmSession]` I opcioni `session: OrmSession | None = None`
keyword-only parametar (isti obrazac kao `_revoke_active_sessions` helper
iz `auth.py`):
- Ako je `session` prosljeđen (nije `None`): koristi POSTOJEĆU sesiju,
  `session.add(...)`, **NE commit-uje** — pozivalac (014C) kontroliše
  commit granicu, audit red ulazi u isti commit kao izmjena termina.
- Ako `session` NIJE prosljeđen: otvara sopstvenu `with session_factory()
  as session:`, `session.add(...)`, `session.commit()` — samostalna
  upotreba (014B slučaj, ili budući pozivaoci bez okolne transakcije).

Ovo je asimetrično od `_revoke_active_sessions` (koji UVIJEK prima
sesiju, nema samostalni mod) jer `write_audit_event` mora pokriti OBA
poziva iz 014B/014C — otud dva parametra umjesto jednog private/public
para funkcija. Alternative razmotrene u sekciji "Odbačene opcije".

## Trenutno stanje repoa (provjereno)

- `alembic heads` → `e5f6a7b8c9d0 (head)` — potvrđeno, poklapa se sa
  kontraktom.
- Baseline: `pytest tests/ -q` → 396 passed, 2 skipped (čisto).
  `ruff check src/dentaland tests backend` → čisto.
  `mypy src/dentaland backend` → čisto (18 fajlova).
  `agent_sensors.py --all` → 0 blocking findings.
- v3.1 doc (linija 267-277) potvrđen: tačno 9 polja
  (`id, actor_user_id, action, resource_type, resource_id, occurred_at,
  request_id, source_ip, metadata_minimal`), uža backlog akcija-lista
  (7, ne 11) potvrđena kao autoritativna za ovaj task po task kontraktu.

## Šta NE dirati

- `src/dentaland/services/appointments.py`, `auth.py`, `backend/main.py`,
  `desktop/**`, `web/**` — nula instrumentacije u ovom tasku.
- Postojeći `migrations/versions/*.py`, `migrations/env.py`, `alembic.ini`.
- Ne graditi `VIEW_PATIENT`/`EXPORT_PERSONAL_DATA`/
  `DELETE_OR_ANONYMIZE_PERSONAL_DATA`/`VIEW_MEDICAL_DATA` enum vrijednosti
  ni funkcionalnost.
- Ne graditi `CHANGE_ROLE` endpoint/UI (samo dormant enum vrijednost).
- Ne graditi retention/brisanje job.
- Ne graditi `update_audit_event`/`delete_audit_event` — append-only se
  postiže ne-izlaganjem mutacionog API-ja (dokumentovano u docstringu).

## Plan verifikacije

1. `pytest tests/ -q` (pun suite, uključujući novi `test_audit.py`).
2. `ruff check src/dentaland tests backend`.
3. `mypy src/dentaland backend`.
4. `python scripts/agent_sensors.py --all`.
5. Ručna alembic upgrade/downgrade provjera nove migracije na
   privremenoj SQLite bazi.
6. Grep potvrda: nema poziva `write_audit_event`/`AuditEvent` van
   `models.py`/`audit.py`/`test_audit.py` (potvrđuje nula instrumentacije).

## Rollback

`alembic downgrade -1` briše `audit_events` tabelu (nova, prazna pri
uvođenju). Kod-nivo rollback: `git checkout` na fajlove iz
`allowed_paths` (grana se ne mergaš dok review ne prođe).

## Odbačene opcije

**Opcija A (odbačena): samo `session_factory`, bez opcionog `session`.**
Ovo je nacrt iz task kontrakta prije čitanja 014C — bilo bi nedovoljno,
jer 014C eksplicitno zahtijeva atomičnost sa izmjenom termina. Odbačeno
nakon čitanja 014C kontrakta.

**Opcija B (odbačena): dva odvojena para funkcija kao
`_revoke_active_sessions`/`invalidate_all_sessions_for_user`** —
`_write_audit_event_in_session(session, ...)` (privatna, ne commit-uje) +
`write_audit_event(session_factory, ...)` (javna, otvara sesiju,
commit-uje). Razmotreno i skoro identično finalnom rješenju — razlika je
samo da li je "in-session" varijanta privatna (Opcija B) ili javna kroz
opcioni parametar iste funkcije (izabrano). Izabrano opcioni parametar
JER 014C treba pozvati JAVNU funkciju sa svojom sesijom (ne bi trebalo da
uvozi "privatni" helper iz drugog modula — `_` prefiks signalizira
internu upotrebu istog modula, ne cross-modul javni ugovor). Funkcionalno
ekvivalentno, ovo je čistiji javni API za cross-modul pozivaoca.

**Opcija C (odbačena): `write_audit_event` UVIJEK zahtijeva postojeću
sesiju (kao `_revoke_active_sessions`), pozivalac uvijek otvara svoju.**
Odbačeno jer bi 014B (login, gdje `write_audit_event` poziv nije nužno
unutar postojeće transakcije — desiće se u route handleru poslije
`authenticate_user` vraća) morao ručno otvarati `session_factory()` samo
da bi pozvao jednu funkciju — nepotrebno opterećenje za samostalni
slučaj koji čini većinu očekivane upotrebe (014B, budući pozivaoci bez
okolne transakcije).

**Opcija D (odbačena): DB-nivo trigera/permisija za append-only umjesto
disciplinom u servisnom sloju.** Neproporcionalno veličini projekta (jedan
VPS, jedna ordinacija) — v3.1/CLAUDE.md princip "ne graditi
enterprise-scale default". Append-only se u ovom obimu postiže NE
izlaganjem `update`/`delete` funkcije u servisnom sloju — direktan SQL
UPDATE/DELETE na tabeli je i dalje tehnički moguć (nema DB-nivo brane),
ali nema ugrađenog API poziva koji bi to slučajno uradio.
