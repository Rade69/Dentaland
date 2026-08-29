---
task_id: DENT-IMPROVE-017
risk: HIGH
implementer: claude
reviewers: [codex]
status: "IMPLEMENTED — oba testa prolaze (449 passed, 0 failed sa DATABASE_URL_TEST), alembic_version pecat tacan na obje lokalne baze. Ceka Codex review, pa human approval. Vidi 2026-08-29-DENT-IMPROVE-017-postgres-fixes.md."
created_at: 2026-08-29
depends_on: DENT-IMPROVE-012, DENT-IMPROVE-013, DENT-IMPROVE-014
---

# DENT-IMPROVE-017 — Stale Postgres RBAC test + alembic pečat neusklađenost

## Kontekst

Otkriveno kao `OUT_OF_SCOPE_FINDING` tokom implementacije
`DENT-IMPROVE-016` (29.8.2026), van njegovog `allowed_paths` — prijavljeno
u `.agent/CURRENT_STATE.md`, ne popravljeno tamo. Potvrđeno da postoji
identično na `main` prije `DENT-IMPROVE-016` (nije regresija koju je taj
task uveo). Radovan je 29.8.2026 tražio da se svi poznati dugovi zatvore.

Dva povezana, ali odvojena nalaza — oba se vide SAMO kad se
`pytest tests/ -q` pokrene sa `DATABASE_URL_TEST` postavljenim (standardan
`pytest tests/ -q` bez te varijable ih ne dodiruje, ostaje nepromijenjen):

1. **`tests/test_postgres_migration.py::test_confirm_preklapanje_vraca_409_nad_postgres`
   puca (401 umjesto 409).** SQLite verzija ovog testa
   (`tests/test_backend.py::test_confirm_preklapanje_vraca_409`) je
   ažurirana kad je `DENT-IMPROVE-013` (RBAC) uveo `RECEPTION`-only zaštitu
   na `/confirm` — dodat je `reception_session` fixture koji se prvo
   uloguje. Postgres-mirror test to nikad nije dobio.
   **Dodatna zamka provjerena unaprijed:** SQLite `client` fixture
   (`test_backend.py`) koristi `TestClient(app, base_url="https://testserver")`
   sa komentarom "standardan obrazac za testiranje secure cookieja kroz
   TestClient" — session cookie u `backend/main.py:233-238` ima
   `secure=True`. Postgres `client` fixture (`test_postgres_migration.py:93`)
   NEMA taj `base_url` — mora se dodati ISTOVREMENO sa auth fixture-om, inače
   login "uspijeva" (200) ali cookie se ne vraća na sljedeći zahtjev i test
   i dalje dobija 401.
2. **Lokalna Postgres instanca (port 5433, `dentaland_test`/`dentaland_dev`)
   ima zastarjel `alembic_version` pečat** — stoji na `d4e5f6a7b8c9`
   (DENT-022), stvaran head je `f6a7b8c9d0e1` (DENT-IMPROVE-014 —
   `audit_events` tabela). Tabele (`users`/`sessions`/`audit_events`) ipak
   postoje jer ih je `Base.metadata.create_all()` u test fixture-ima
   (`pg_engine` u više test fajlova) kreirao mimo alembic-a — migracije za
   `DENT-IMPROVE-013`/`DENT-IMPROVE-014` **nikad nisu stvarno primijenjene
   kroz `alembic upgrade head`** protiv ove instance, samo zaobiđene. Ovo
   direktno uzrokuje drugi postojeći failure:
   `tests/test_postgres_migration.py::test_alembic_database_url_sa_percent_encoded_lozinkom`
   (asertuje da `alembic current` ispisuje `(head)`).

## Cilj

Oba testa prolaze, I stvarno dokazano da cijeli migration chain
(`a1b2c3d4e5f6` do `f6a7b8c9d0e1`) čisto primjenjuje kroz pravi
`alembic upgrade head` na praznoj bazi — ne samo da `create_all()`
zaobilaznica i dalje radi.

## Required scope

1. **Popravka RBAC testa** (`tests/test_postgres_migration.py`):
   - Dodati `pg_reception_session` fixture (isti obrazac kao
     `reception_session` u `test_backend.py`, ali kroz `pg_session_factory`
     — uvoze se `User`, `UserRole`, `hash_password`).
   - `client` fixture: dodati `base_url="https://testserver"` uz
     `TestClient(app)` poziv.
   - `test_confirm_preklapanje_vraca_409_nad_postgres` dobija
     `pg_reception_session: None` parametar (zavisnost, isti obrazac kao
     SQLite original).
   - `_cleanup()` proširiti da briše i test `User` red (marker-tagovan
     username, npr. `f"sestra-test-{_MARKER}"` da ne kolidira sa drugim
     test fajlovima koji dijele istu `dentaland_test` bazu).

2. **Stvarna primjena migracija na lokalnoj instanci** (port 5433):
   - Za `dentaland_test` I `dentaland_dev` (obje, provjeriti obje su
     prazne/samo-sintetičke prije diranja — vidi Šta NE dirati):
     `DROP` sve postojeće tabele (ili cijelu bazu pa `CREATE DATABASE`
     ponovo — implementer bira, dokumentuje zašto) tako da je baza
     stvarno prazna (bez `alembic_version` reda).
   - Pokrenuti pravi `alembic upgrade head` (ne `create_all()`) i
     potvrditi da prolazi bez greške na SVAKOJ migraciji u lancu, ne samo
     zadnjoj.
   - `alembic current` mora ispisati stvaran head (`f6a7b8c9d0e1 (head)`).
   - Pokrenuti pun `pytest tests/ -q` sa `DATABASE_URL_TEST` postavljenim
     i potvrditi da SVI testovi (uklj. `DENT-IMPROVE-016` backup testove
     koji zavise od kompletne šeme) i dalje prolaze nad ovako
     migriranom (ne `create_all()`-ovanom) bazom.

## Šta NE dirati

- Prije DROP-a na `dentaland_dev`, PONOVO provjeriti da je prazna
  (`SELECT COUNT(*) FROM appointments`/`doctors` — već potvrđeno 0 tokom
  `DENT-IMPROVE-016`, ali provjeriti opet, stanje se moglo promijeniti).
  Ako NIJE prazna ili sadrži bilo šta što ne izgleda sintetički, STATI i
  prijaviti Radovanu — ne brisati bez potvrde (vidi
  `docs/dentaland-politika-produkcijski-podaci.md`, DENT-IMPROVE-016).
- `migrations/versions/**` — postojeći migracioni fajlovi se NE mijenjaju,
  samo se stvarno IZVRŠAVAJU. Ako neka migracija ima grešku koja sprečava
  čisto izvršavanje, to je NOVI nalaz — prijaviti, ne tiho zaobići.
- `src/dentaland/services/availability.py` — overlap logika koju
  `test_confirm_preklapanje_vraca_409_nad_postgres` provjerava, ostaje
  netaknuta (isti forbidden path kao originalni `DENT-IMPROVE-012`).
- Ne dirati `tests/test_backend.py` (SQLite original) — samo Postgres
  mirror se popravlja.

## Acceptance criteria

- [ ] `pytest tests/test_postgres_migration.py -v` sa `DATABASE_URL_TEST`
      → svi testovi passed, uklj. oba prethodno crvena
- [ ] `alembic current` (sa `DATABASE_URL` = lokalna instanca) ispisuje
      `f6a7b8c9d0e1 (head)` (ili trenutni stvaran head ako se u
      međuvremenu promijenio)
- [ ] `pytest tests/ -q` sa `DATABASE_URL_TEST` postavljenim → 0 failed
      (trenutno 2 od ~447)
- [ ] `pytest tests/ -q` BEZ `DATABASE_URL_TEST` → nepromijenjen baseline
      (broj passed/skipped identičan prije/poslije)
- [ ] `ruff`, `mypy`, `agent_sensors.py --all` čisti
- [ ] Evidence izvještaj dokumentuje TAČNO koje komande su pokrenute za
      drop/recreate/upgrade (reproducibilnost — sljedeći put kad neko
      dirne ovu instancu treba znati kako je stvarno dovedena u ispravno
      stanje)

## Allowed paths

```text
tests/test_postgres_migration.py
agent_reports/**
```

(Plus admin operacije nad lokalnom Postgres instancom — port 5433,
`dentaland_test`/`dentaland_dev` — koje nisu fajlovi u repou, ali su dio
obima: DROP/CREATE DATABASE, `alembic upgrade head`.)

## Forbidden paths

```text
migrations/versions/**
src/dentaland/services/availability.py
tests/test_backend.py
models.py
```

## Review

Codex (jedini reviewer — pravilo od 29.8.2026,
`docs/dentaland-agentski-razvoj.md`). Human approval prije bilo kakvog
merge-a (ovaj task nema poseban merge korak osim git commit-a testa —
DROP/recreate na lokalnoj instanci se ne "merguje", ali evidence mora
biti jasan o tome šta je urađeno protiv baze). Codex posebno provjerava:
(a) da li je `pg_reception_session` fixture stvarno ekvivalentan
originalu (isti `secure=True` cookie problem), (b) da li je DROP/recreate
sekvenca bezbjedna i reproducibilna, (c) da testovi ne kolidiraju sa
drugim test fajlovima koji dijele istu `dentaland_test` bazu (marker
imena).

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-017 --agent claude --paths tests/test_postgres_migration.py
```

Nema poznatih zavisnosti sa drugim aktivnim taskovima.
