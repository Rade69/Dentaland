---
task_id: DENT-IMPROVE-019
risk: HIGH
implementer: claude
reviewers: [codex]
status: "Implementacija gotova, evidence spreman, ceka Codex review + human approval"
created_at: 2026-08-30
---

# DENT-IMPROVE-019 — TZDateTime timestamptz fix — evidence

Vidi `agent_reports/DENT-IMPROVE-019-task-contract.md` za pun kontekst,
root cause analizu i required scope.

## Šta je implementirano

1. **`src/dentaland/models.py`** — `TZDateTime.impl` promijenjen sa
   `DateTime` na `DateTime(timezone=True)`. `process_result_value`
   normalizuje na `.astimezone(UTC)` i za tz-aware ulaz (ne samo
   `tzinfo is None` granu) — docstring garancija "vraća se kao
   timezone-aware UTC" sad je stvarno tačna za svaki mogući ulazni
   offset, ne samo za slučaj kad Postgres vrati `+00:00`.

2. **Migracija** `migrations/versions/g7h8i9j0k1l2_tzdatetime_timestamptz.py`
   — `ALTER COLUMN ... TYPE timestamptz USING <col> AT TIME ZONE 'UTC'`
   za svih 14 `TZDateTime` kolona (`time_off.od_datetime/do_datetime`,
   `appointments.start_time/end_time/confirmed_at/arrived_at/
   reminder_sent_at/created_at/updated_at`, `users.created_at`,
   `sessions.expires_at/created_at/revoked_at`, `audit_events.occurred_at`).
   No-op na SQLite (nema stvarnu timestamptz/timestamp razliku u
   skladištu). Namjerno NE koristi `batch_alter_table(recreate="always")`
   obrazac iz ranijih migracija — to na Postgresu ide preko privremene
   tabele i RESETUJE SERIAL sekvence (stvarno pogođeno tokom
   DENT-IMPROVE-018 test VPS deploya, morao sam ručno `setval`-ovati
   `appointments_id_seq` — vidi taj task-ov evidence). Direktan
   `ALTER COLUMN TYPE` ne dira sekvence.

3. **`tests/test_tzdatetime_postgres.py`** (nov, 4 testa, SVI
   Postgres-only — `skipif` bez `DATABASE_URL_TEST`, isti obrazac kao
   `test_postgres_migration.py`):
   - `test_sesija_je_stvarno_ne_utc` — sanity-check da test fixture
     stvarno postavlja sesijsku `TimeZone` na `America/New_York`
     (`connect_args={"options": "-c timezone=..."}"`).
   - `test_migracija_postavlja_timestamptz_kolonu` — stvaran
     `alembic upgrade head`, provjerava preko `inspect()` da je kolona
     STVARNO `timestamptz` (`DateTime.timezone is True`), ne samo da
     migracija ne baci grešku.
   - `test_round_trip_ne_pomjera_vrijeme_kad_sesija_nije_utc` —
     REGRESIONI test za tačan otkriveni scenario (11:00 UTC → mora
     ostati 11:00 UTC, ne 07:00/13:00 zavisno od sesijske zone).
   - `test_round_trip_razliciti_offset_ulaz_i_uvijek_vraca_utc` —
     proizvoljan ulazni offset (`Asia/Tokyo`), provjerava i vrijednost
     i da povratni `tzinfo` uvijek bude `UTC`.

## Dokaz da je regresioni test stvaran (adversarna metodologija)

Isti obrazac kao DENT-IMPROVE-013 F1 fix
(`agent_reports/2026-08-27-DENT-IMPROVE-013-auth-rbac.md`) — test je
LIČNO pokrenut protiv STAROG koda prije fixa:

```
git stash                          # privremeno vrati models.py na impl=DateTime
pytest tests/test_tzdatetime_postgres.py::test_round_trip_ne_pomjera_vrijeme_kad_sesija_nije_utc -v
```

Rezultat: **FAILED** —
`assert datetime(2026, 8, 31, 7, 0, tzinfo=UTC) == datetime(2026, 8, 31, 11, 0, tzinfo=UTC)`
(11:00 UTC upisano, 07:00 UTC pročitano — `America/New_York` je UTC-4 u
avgustu, tačno očekivan smjer/veličina pomjeraja za taj bug).

Nakon `git stash pop` (fix vraćen) + primijenjena migracija: **PASSED**.

## Verifikacija

- `pytest tests/ -q` bez `DATABASE_URL_TEST` (SQLite): **429 passed, 24
  skipped** (4 više skipped nego prije — novi Postgres-only testovi,
  očekivano; 0 novih failure-a).
- `pytest tests/ -q` sa `DATABASE_URL`+`DATABASE_URL_TEST` (real lokalni
  Postgres, `dentaland_test`, port 5433, `Europe/Budapest` sesijska
  zona po default-u): **453 passed, 0 failed**.
- `ruff check .` — 5 pre-postojećih grešaka u `scripts/coordination.py`
  (nepovezano, `datetime.UTC` alias prijedlozi), svi fajlovi ovog
  taska čisti.
- `mypy src backend` — **Success: no issues found in 20 source files**.
- `python scripts/agent_sensors.py --all` — **0 blocking findings**.

## Šta NIJE testirano / napomena o dijeljenoj test bazi

**Test VPS (`dentaland_vpstest`, Postgres, `Europe/Berlin`)**: migracija
NIJE primijenjena tamo u ovom krugu. VPS trenutno ima DENT-IMPROVE-018
granu checkout-ovanu (privremeno, za taj task-ov end-to-end test — vidi
`agent_reports/2026-08-30-DENT-IMPROVE-018-implementation.md`); ova
grana (DENT-IMPROVE-019) je odvojen worktree/grana od `main`, i obje
diraju `migrations/versions/` sa istim `down_revision` roditeljem
(`f6a7b8c9d0e1`) — spajanje na VPS-u zahtijeva usklađen redoslijed koji
ima smisla riješiti tek pri stvarnom merge-u u `main` (vidi
"Koordinacija" sekciju u Task Contractu), ne u ovom test krugu.
Lokalna Postgres verifikacija (Budapest zona) je dovoljna da dokaže fix
radi na PRAVOM ne-UTC serveru — isti mehanizam koji je pogodio VPS.

**Napomena o dijeljenoj lokalnoj `dentaland_test` bazi između worktree-ova**:
tokom testiranja, dvije paralelne grane (DENT-IMPROVE-018 i
DENT-IMPROVE-019) su se sudarile na `alembic_version` pokazivaču iste
fizičke test baze (svaka grana zna samo za svoj dio migracijskog
lanca). Riješeno privremenim `alembic downgrade` na zajedničkog pretka
(`f6a7b8c9d0e1`) prije pokretanja ovog task-a; `dentaland_dev` (lokalni
scratch, DATABASE_URL) je nenamjerno prvo pogođen istom komandom pa
vraćen na DENT-IMPROVE-018 head odmah nakon. Bez uticaja na bilo šta
committovano — čisto lokalna, self-healing situacija (svaka grana radi
ispravno kad se pokrene samostalno).

## Sljedeći koraci

1. Codex review (jedini reviewer).
2. Human approval.
3. Redoslijed merge-a sa DENT-IMPROVE-018 treba pažnju (obje grane
   granaju iz `f6a7b8c9d0e1`) — koji god se prvi mergira u `main`,
   drugi treba rebase svoju migraciju da nastavi lanac prije svog
   merge-a.
4. Kad se merge-uje: primijeniti na test VPS (`dentaland_vpstest`) i
   ponovo potvrditi da termini stvarno prikazuju tačno vrijeme (isti
   test kao DENT-IMPROVE-018 end-to-end, ali sad bez 2h pomjeraja).
