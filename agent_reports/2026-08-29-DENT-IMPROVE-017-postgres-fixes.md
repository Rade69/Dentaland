---
task_id: DENT-IMPROVE-017
implementer: claude
created_at: 2026-08-29
---

# DENT-IMPROVE-017 — implementerov izvještaj

## Urađeno

### 1. Stvarna primjena migracija na lokalnoj instanci (port 5433)

Prije bilo čega, provjereno da su obje baze prazne/sintetičke (vidi
"Sigurnosna provjera" ispod). `dentaland_dev` je bila stvarno prazna
(0 appointments/doctors, tabela `users` nije ni postojala). `dentaland_test`
je imala ostatak prekinutog test run-a (1 appointment "Test Pacijent",
6 doktora "Test Doktor 1/2") — potvrđeno sintetičko po imenu/telefonu
prije brisanja.

Tačne komande (`dentaland_app` nalog ima `CREATEDB`/ownership nad obje
baze, nije trebao superuser):

```bash
# Konektuj se na SUSJEDNU bazu da drop-uješ ovu (ne možeš drop-ovati bazu
# na koju si trenutno konektovan)
psql --dbname="$DATABASE_URL_TEST" --command="DROP DATABASE dentaland_dev;" \
                                    --command="CREATE DATABASE dentaland_dev OWNER dentaland_app;"
psql --dbname="$DATABASE_URL" --command="DROP DATABASE dentaland_test;" \
                               --command="CREATE DATABASE dentaland_test OWNER dentaland_app;"

# Pravi alembic upgrade head (ne create_all()) na obje, redom
DATABASE_URL="<dentaland_dev url>" python -m alembic upgrade head
DATABASE_URL="<dentaland_test url>" python -m alembic upgrade head
```

Rezultat — cijeli lanac od 6 migracija primijenjen čisto na OBJE baze,
bez greške na ijednoj:

```text
-> a1b2c3d4e5f6  Initial schema
-> b2c3d4e5f6a7  Faza 1 (priprema)
-> c3d4e5f6a7b8  DENT-012 confirmed_at/arrived_at
-> d4e5f6a7b8c9  DENT-022 reminder_sent_at
-> e5f6a7b8c9d0  DENT-IMPROVE-013 users/sessions
-> f6a7b8c9d0e1  DENT-IMPROVE-014 audit_events
```

`alembic current` na obje bazama sad ispisuje `f6a7b8c9d0e1 (head)`.
`\dt` potvrđuje istih 9 tabela kao ranije (kroz `create_all()`) — šema je
ekvivalentna, samo sad stvarno dokazano da migration chain radi od nule,
ne samo pretpostavljeno.

### 2. Popravka RBAC testa (`tests/test_postgres_migration.py`)

- Dodat `pg_reception_session` fixture (Postgres pandan
  `reception_session` iz `test_backend.py`).
- `client` fixture: dodat `base_url="https://testserver"` — session
  cookie ima `secure=True` (DENT-IMPROVE-013), TestClient ga bez toga ne
  vraća/šalje preko sljedećih poziva. Ovo je bio DODATNI, prethodno
  neprepoznat dio problema — samo dodavanje login fixture-a bez ovoga i
  dalje ne bi radilo.
- `test_confirm_preklapanje_vraca_409_nad_postgres` dobija
  `pg_reception_session: None` zavisnost.
- `_cleanup()` proširen za `User` red — **usput otkriven i popravljen
  FK redoslijed bug tokom implementacije**: `DELETE FROM users` je prvo
  pucao na `sessions_user_id_fkey` (login kreira `Session` red), pa nakon
  te popravke na `audit_events_actor_user_id_fkey` (login upisuje i
  `LOGIN_SUCCESS` audit zapis, DENT-IMPROVE-014B). Cleanup sad briše
  `Session` i `AuditEvent` redove vezane za test korisnika PRIJE samog
  korisnika. `dentaland.models.Session` uvezen pod aliasom
  (`Session as UserSessionModel`) da se izbjegne kolizija imena sa već
  uvezenim `sqlalchemy.orm.Session`.

## Sigurnosna provjera prije DROP-a

Prema `docs/dentaland-politika-produkcijski-podaci.md`
(DENT-IMPROVE-016) — provjereno PRIJE brisanja:

- `dentaland_dev`: `SELECT COUNT(*) FROM appointments/doctors` → oba 0.
  Tabela `users` nije ni postojala (ranija provjera nikad nije stigla do
  DENT-IMPROVE-013 modela).
- `dentaland_test`: `SELECT id, ime FROM doctors` → sve `"Test Doktor
  1/2"`. `SELECT id, ime, telefon FROM appointments` → `"Test Pacijent"`,
  telefon `"061"` (fiktivan placeholder korišten kroz cijeli test suite).
  Jasno sintetički, ostatak prekinutog test run-a — sigurno za brisanje.

## Verifikacija

- `pytest tests/test_postgres_migration.py -v` sa `DATABASE_URL_TEST` →
  **2 passed** (oba prethodno crvena).
- `pytest tests/ -q` sa `DATABASE_URL_TEST` → **449 passed, 0 failed**
  (prethodno 447 passed, 2 failed).
- `pytest tests/ -q` bez `DATABASE_URL_TEST` → **429 passed, 20 skipped**
  — identičan baseline (429 passed nepromijenjen; 20 skipped = 2
  Postgres-migration + 18 DENT-IMPROVE-016 backup testova, svi
  Postgres-zavisni, preskaču se bez env varijable kao i prije).
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`
  → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in
  55 source files**.
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.

## Codex review — PASS_WITH_NOTES, N1 (operativna preporuka, ne blocker)

Codex je potvrdio PASS bez blocking nalaza (fixture ekvivalencija,
FK-safe cleanup, marker kolizije, stvaran alembic head — sve provjereno
nezavisno, uklj. dva uzastopna runa). Jedna napomena za budućnost: DROP
komande dokumentovane iznad ("Sigurnosna provjera" sekcija) su tekstualne
i ne provjeravaju same host/port/naziv baze niti koriste
`psql --set ON_ERROR_STOP=1` — bezbjedne su za ono što su upravo uradile
(provjereno lokalno okruženje, port 5433, sadržaj provjeren prije
brisanja), ali se ne smiju slijepo kopirati u drugo okruženje. Za buduće
ponavljanje: prvo ispisati/validirati target host/port/database/owner,
ponoviti provjeru sadržaja, koristiti fail-fast `psql`.

## Required output

```yaml
verdict: PASS
blocking_findings: []
evidence:
  - tests/test_postgres_migration.py (2 passed, oba prethodno crvena)
  - lokalna Postgres instanca (port 5433) - alembic_version pecat sad tacan na obje baze
  - pytest tests/ -q sa DATABASE_URL_TEST - 449 passed, 0 failed
open_risks: []
```

## Sljedeće

Codex review (jedini reviewer), zatim Radovanovo human approval.
