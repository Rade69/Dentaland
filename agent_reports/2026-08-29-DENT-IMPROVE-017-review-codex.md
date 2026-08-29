---
task_id: DENT-IMPROVE-017
reviewer: codex
review_type: independent_high_risk_review
reviewed_commit: 95b968ec3832e2af968b470059686f8f4b2a903c
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
blocking_findings: []
reviewed_at: 2026-08-29
---

# DENT-IMPROVE-017 — Codex review

## CILJ

Nezavisno provjeriti popravku stale PostgreSQL RBAC testa i stvarno stanje
Alembic migracija na lokalnim `dentaland_dev`/`dentaland_test` bazama.

## VERDIKT

**PASS_WITH_NOTES.** Nema blocking nalaza. Oba prethodna failure-a su
zatvorena, fixture cleanup je FK-ispravan, obje baze imaju očekivanog
nesuperuser vlasnika i stvarni Alembic head, a oba puna baselinea prolaze.

## PROVJERE

### 1. `pg_reception_session` i secure cookie — PASS

Fixture je funkcionalno ekvivalentan `reception_session` iz
`tests/test_backend.py`:

- kreira `UserRole.RECEPTION` korisnika preko istog `hash_password` toka;
- poziva stvarni `/api/auth/login` endpoint;
- asertuje HTTP 200;
- isti `TestClient` zadržava session cookie za naredni `/confirm` poziv;
- `base_url="https://testserver"` odgovara SQLite originalu i nužan je jer
  produkcijski session cookie ima `secure=True`.

Popravljeni test stiže do poslovnog overlap contracta i vraća očekivani 409,
umjesto ranijeg 401.

### 2. FK-safe cleanup — PASS

Model ima dvije FK reference prema test korisniku: `sessions.user_id` i
nullable `audit_events.actor_user_id`. `_cleanup` prvo briše oba skupa po
subqueryju marker username-a, zatim korisnika. Appointment/Doctor/Service
marker podaci čiste se u istoj transakciji.

Ako setup završi samo djelimično, `pg_session_factory` finalizer je već
aktiviran prije zavisnih fixture-a i sljedeći startup ponavlja isti idempotentni
cleanup. Dva uzastopna ciljna runa su oba prošla:

```text
2 passed
2 passed
```

Time je potvrđeno da login-created Session/AuditEvent redovi ne ostavljaju FK
violation niti residue između runova.

### 3. Marker kolizije — PASS

`sestra-test-Postgres Overlap Test` pojavljuje se samo u
`tests/test_postgres_migration.py`. SQLite backend test koristi različit
username `sestra-test`; ostali Postgres testovi koriste druge markere. Nema
kolizije sa drugim test fajlom koji dijeli `dentaland_test`.

Statičan marker nije dizajniran za dva istovremena procesa/xdist workera nad
istom eksternom bazom, ali projekat trenutno ne pokreće taj test tim načinom;
to nije regresija niti acceptance zahtjev ovog taska.

### 4. Lokalna PostgreSQL migracija i ownership — PASS

Read-only provjera stvarnog stanja dala je:

```text
DATABASE_URL      dentaland_dev   owner=dentaland_app
DATABASE_URL_TEST dentaland_test  owner=dentaland_app
```

`alembic current` na obje baze:

```text
f6a7b8c9d0e1 (head)
```

Dakle baze nisu samo `create_all()`-ovane sa starim pečatom; pečat odgovara
stvarnom trenutnom migration headu. Izvještaj dokumentuje cross-database
DROP/CREATE i odvojeni `alembic upgrade head` za obje baze. `dentaland_app`
je vlasnik, ne superuser.

## NAPOMENA N1 — operativne DROP komande nisu samostalno guardovan alat

Dokumentovana sekvenca je bezbjedno izvršena u provjerenom lokalnom okruženju
na portu 5433 nakon provjere da su podaci prazni/sintetički. Ipak, tekstualne
komande same ne provjeravaju host/port/nazive baze i ne koriste
`psql --set ON_ERROR_STOP=1`; ne treba ih slijepo kopirati u drugo okruženje.

Za buduće ponavljanje prvo ispisati/validirati target host, port, database i
owner, ponoviti provjeru sadržaja, pa koristiti fail-fast psql. Ovo je
operativna preporuka, ne blocker za već izvršenu i nezavisno potvrđenu lokalnu
migraciju.

## SCOPE

Commit mijenja samo:

- `tests/test_postgres_migration.py`;
- Task Contract i implementerov izvještaj.

Forbidden produkcijski, migracioni i SQLite-test fajlovi nisu dirani.

## SVJEŽA VERIFIKACIJA

- `pytest tests/test_postgres_migration.py -q` sa `DATABASE_URL_TEST`, dva
  uzastopna runa → **2 passed**, zatim ponovo **2 passed**.
- `pytest tests/ -q` sa `DATABASE_URL_TEST` → **449 passed**.
- `pytest tests/ -q` bez `DATABASE_URL_TEST`/`DATABASE_URL` →
  **429 passed, 20 skipped**.
- Ruff → **All checks passed**.
- Mypy → **no issues found in 55 source files**.
- Agent sensors → **0 blocking findings**.
- Branch CI → prema dostavljenom evidence-u zelen.

Nije potvrđen code defect u pregledanom scope-u.

## HANDOFF

**CILJ:** zatvoriti stale RBAC test i dokazati stvaran Alembic chain/head.

**URAĐENO:** PASS_WITH_NOTES — acceptance je ispunjen, bez blocking nalaza.

**NE DIRATI:** migracione fajlove, availability servis i SQLite originalni
backend test; nisu zahtijevali izmjene.

**SLJEDEĆE:** Radovanov human approval. Reviewerov verdict ne autorizuje
merge/deploy sam po sebi.
