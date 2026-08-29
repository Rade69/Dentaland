---
task_id: DENT-IMPROVE-016
implementer: claude
created_at: 2026-08-29
---

# DENT-IMPROVE-016 — Produkcijski security/privacy release gate (skraćen obim) — implementerov izvještaj

## Urađeno

1. **`src/dentaland/backup_postgres.py`** — nov modul, `pg_dump`/`pg_restore`
   (subprocess) + Fernet enkripcija (poseban ključ, `backup_postgres.key`)
   + pojednostavljena rotacija ("zadrži zadnjih N", bez SQLite-ovog
   dnevno/mjesečnog sloja) + CLI (`run`/`restore-test`/`status`), po uzoru
   na `dentaland.backup`/`backup_cli`. `restore-test` kreira PRIVREMENU
   bazu (`CREATE DATABASE`), restore-uje u nju, verifikuje, pa je briše —
   nikad ne dira aktivnu bazu.
2. **`tests/test_backup_postgres.py`** — 6 testova, preskaču se ako
   `DATABASE_URL_TEST` nije postavljen (isti obrazac kao
   `test_postgres_migration.py`). Pokrivaju: run→restore-test uspjeh
   + potvrda da privremena baza stvarno nestane, da aktivna baza ostaje
   netaknuta, grešku kad nema backupa, rotaciju, grešku bez
   `DATABASE_URL`, i CLI put (`main()`).
3. **`docs/dentaland-postgres-backup-operativni-vodic.md`** — operativni
   vodič, po uzoru na postojeći SQLite backup vodič.
4. **`docs/dentaland-breach-runbook.md`** — koraci: detekcija,
   containment, procjena, 72h prijava Agenciji, obavještavanje pacijenata,
   interna evidencija, post-incident pregled.
5. **`docs/dentaland-retention-politika.md`** — formalizuje petogodišnji
   rok za booking podatke (ispravljeno sa pogrešnih "12 mjeseci" —
   vidi CLAUDE.md commit `0c83433`), potvrđuje da medicinska
   dokumentacija nije primjenjiva (ostaje na papiru van sistema),
   eksplicitno navodi da automatska anonimizacija/brisanje NIJE
   implementirana u kodu.
6. **`docs/dentaland-politika-produkcijski-podaci.md`** — formalizuje
   pravilo "stvarni podaci nikad u AI/dev dumpove", sa referencom na
   stvaran DENT-IMPROVE-012 presedan (14 pronađenih pacijentskih zapisa,
   ispravno neiskorišteno).

## Audit `web/privacy.html` (stavka 5 — provjera, ne pisanje)

Dokument je **kompletan** naspram CLAUDE.md/v3.1 zahtjeva. Pokriva svih
9 relevantnih tačaka: kontrolor (sekcija 1), koje podatke prikuplja +
eksplicitno upozorenje da ne unositi medicinske podatke (sekcija 2),
svrha (sekcija 3), pravni osnov (sekcija 4), koji podaci su obavezni
(sekcija 5), primaoci/obrađivači (sekcija 6), retention — pet godina
(sekcija 7, **potvrđeno tačno** 29.8.2026, vidi retention politiku
gore), prava lica (sekcija 8), pravo na prigovor Agenciji sa tačnim
kontaktom (sekcija 9), automatizovano odlučivanje (sekcija 10),
maloljetna lica (sekcija 11).

Dodatno potvrđeno: `web/tests/e2e/tests/booking.spec.js` test #7
(DENT-IMPROVE-011) već provjerava da link ka `privacy.html` postoji i
radi sa forme za zakazivanje — nije izolovan, nepovezan fajl.

**Nema stvarnog nalaza koji bi tražio izmjenu dokumenta.** Manja
napomena (nije defekt, samo zapažanje): sekcija 1 identifikuje
kontrolora imenom/adresom, ne formalnim registarskim brojem pravnog
subjekta — ovo je dosljedno sa CLAUDE.md "Otvorena pitanja" stavkom
"kontrolor/obrađivač ugovor" koja ostaje otvorena (potvrditi pravni
subjekt ordinacije). Nije nešto što ovaj task treba/smije mijenjati.

## OUT_OF_SCOPE_FINDING (prijavljen tokom rada, van allowed_paths)

Otkriveno tokom regresionog testiranja (`pytest tests/ -q` sa
`DATABASE_URL_TEST` postavljenim) — **potvrđeno da postoji identično na
`main` prije ovog taska**, nije izazvano ovim radom:

1. `tests/test_postgres_migration.py::test_confirm_preklapanje_vraca_409_nad_postgres`
   puca (401 umjesto 409) — Postgres-mirror test nije ažuriran za RBAC
   kredencijale kad je `DENT-IMPROVE-013` mergovan.
2. Lokalna Postgres instanca ima zastarjel `alembic_version` pečat
   (`d4e5f6a7b8c9`, DENT-022) naspram stvarnog head-a (`f6a7b8c9d0e1`,
   DENT-IMPROVE-014) — tabele postoje jer ih je `Base.metadata.create_all()`
   u test fixture-ima kreirao mimo alembic-a; migracije DENT-IMPROVE-013/014
   nikad nisu stvarno testirane u svom pravom (`alembic upgrade head`)
   obliku protiv ove instance.

Zabilježeno u `.agent/CURRENT_STATE.md` (commit `a373882`), predložen
budući `DENT-IMPROVE-017`. Ne blokira ovaj task.

## Verifikacija

- `pytest tests/test_backup_postgres.py -v` (sa `DATABASE_URL_TEST`) →
  **6 passed**.
- `pytest tests/ -q` (bez `DATABASE_URL_TEST`, SQLite-only baseline) →
  **429 passed, 8 skipped** (6 novih backup testova + postojeća 2 se
  preskaču bez env varijable — nepromijenjen baseline).
- `pytest tests/ -q` (sa `DATABASE_URL_TEST`) → **435 passed, 2 failed**
  — dva failure-a su OUT_OF_SCOPE_FINDING gore, potvrđeno identično na
  `main` prije ovog taska.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`
  → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in
  55 source files**.
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.

## Required output

```yaml
verdict: PASS_WITH_NOTES
blocking_findings: []
evidence:
  - src/dentaland/backup_postgres.py
  - tests/test_backup_postgres.py (6 passed)
  - docs/dentaland-postgres-backup-operativni-vodic.md
  - docs/dentaland-breach-runbook.md
  - docs/dentaland-retention-politika.md
  - docs/dentaland-politika-produkcijski-podaci.md
  - web/privacy.html audit — kompletan, bez izmjena
open_risks:
  - "HTTPS, processor evidencija, EXCLUDE constraint namjerno van obima - cekaju Radovanovu hosting odluku (kraj projekta)"
  - "Automatska anonimizacija/brisanje nakon 5 godina nije implementirana u kodu - samo politika, buduci implementacioni task"
  - "token sigurnost i minimalna javna forma nisu formalno auditovani ovim gate-om (vjerovatno OK, ranije provjereno indirektno kroz DENT-IMPROVE-011 E2E)"
  - "OUT_OF_SCOPE_FINDING: stale Postgres RBAC test + alembic pecat neusklađenost (buduci DENT-IMPROVE-017), potvrđeno predpostojece na main"
```

## Sljedeće

Codex (Reviewer 1) pa Crush (Reviewer 2), zatim Radovanovo human
approval prije merge-a.
