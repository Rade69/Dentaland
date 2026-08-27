---
task_id: DENT-IMPROVE-012
risk: HIGH
reviewer: pi
role: Reviewer 2 (arhitektura/scope)
verdict: PASS_WITH_NOTES
date: 2026-08-27
---

# DENT-IMPROVE-012 — Pi nezavisan review (arhitektura/scope)

Nezavisan pregled, izveden od nule — nisam čitao Codex/Claude rezonovanje prije
sopstvene provjere (presedan iz REF-03: fresh reviewer).

**Verifikovano LIČNO (ne iz izvještaja):** Pregled radnog stanja grane
`task/DENT-IMPROVE-012-postgres-migration`, stvarni diff, grep cijelog koda,
stvarna reprodukcija migracionog skripta nad izolovanom bazom (port 5433,
potvrđeno running PID 8076), read-only pregled glavnog `dentaland.db`.

## Scope / obim — PROLAZI

- **Nema EXCLUDE/`btree_gist` nigdje u kodu.** Grep cijelog diff-a i svih
  novih/izmijenjenih fajlova (`backend/main.py`, `migrations/env.py`,
  `pyproject.toml`, `scripts/migrate_sqlite_to_postgres.py`,
  `tests/test_postgres_migration.py`) → jedina pojava riječi `btree_gist`/
  `EXCLUDE` je **komentar u `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`** koji
  objašnjava da je namjerno izostavljen. Nula tragova u šemi/models.
  Potvrđeno i preko `pg_constraint` izvještaja implementera (jedini
  `c`-tip constraint na `appointments` je CHECK enum).
- **Samo migracija konekcije + podataka.** `backend/main.py`: `DATABASE_URL`
  ima prednost, else identičan SQLite (`DENTALAND_DB_PATH`) — aditivno,
  ne mijenja default. `migrations/env.py`: standardni Alembic `DATABASE_URL`
  override, alembic.ini SQLite default netaknut.
- **`psycopg2-binary`** u `pyproject.toml` — izbor dokumentovan i opravdan
  (plain `postgresql://` URL bez prefiksa, psycopg2 ne zahtijeva izmjenu
  `.env` formata).

## Forbidden paths — PROLAZI

`git diff HEAD` za svaku forbidden putanju → **prazan**:

- `src/dentaland/models.py` — netaknut (TZDateTime portabilan, kako je
  kontrakt i pretpostavio)
- `src/dentaland/services/availability.py` — netaknut
- `desktop/**` — netaknut
- `web/**` — netaknut
- `migrations/versions/**` — netaknut (grep i diff prazni; postojeće 4
  migracije nisu dirane)
- `src/dentaland/backup.py`, `backup_cli.py` — netaknuti
- `alembic.ini` — netaknut

## Arhitektonska ocjena `scripts/migrate_sqlite_to_postgres.py` — PROLAZI

Reprodukovano lično nad stvarnom bazom (ne čitano iz izvještaja):

| Tačka | Ocjena |
|---|---|
| **FK-safe redoslijed** (Doctor→Service→WorkingHours→TimeOff→Appointment) | ✓ tačan i obrnut za truncate |
| **Read-only izvor** (`mode=ro`) | ✓ potvrđeno: čitanje radi, pisanje baca `OperationalError: attempt to write a readonly database` |
| **Core (Table) nivo, ne ORM identity map** | ✓ dobra odluka — izbjegava vezivanje objekta za dvije sesije istovremeno |
| **`_reset_sequences`** | ✓ potvrđeno: nakon migracije sa `max(id)=6`, prirodan INSERT dobije `id=7` — nema kolizije |
| **Integrity (ne samo "nije pukao")** | ✓ row counts + FK spot-check (`NOT EXISTS`) + status counts — lično reprodukovan `Overall: OK` sa 6/3/1/0/1 redova |
| **Alembic upgrade head nad Postgres** | ✓ `d4e5f6a7b8c9 (head)` na portu 5433 |

**Usputna napomena (ne blokira, N1):** `run_migration` zove
`Base.metadata.create_all(target_engine)` prije kopiranja. To je no-op ako je
Alembic već kreirao šemu (kako je ovde i bilo), ali skript time **ne
garantuje** da je šema građena kroz migracije — oslanja se na to da je
`alembic upgrade head` već pokrenut od strane korisnika. Za jednokratan CLI
primarno testiran nad `dentaland_test` ovo je prihvatljivo i dokumentovano;
nije buduća zamjena za Alembic. Preporuka: u docstring/skoru dodati napomenu
da skript pretpostavlja primijenjenu šemu (ne kreira je kao autoritet).

## Standardni gateovi (reprodukovano)

- `pytest tests/ -q` sa `DATABASE_URL_TEST` → **376 passed** (374 baseline +
  2 nova Postgres testa)
- `pytest tests/test_postgres_migration.py` sa `DATABASE_URL_TEST` →
  **2 passed** (409-conflict + percent-encoded F1 regresija)
- Backward-compat: bez `DATABASE_URL_TEST` novi testovi se **preskaču**
  (`skipif`), ne pucaju — default SQLite put neoštećen
- `.env` gitignored (potvrđeno `git check-ignore`), nije u diff-u/staged

## Nalazi

- **N1 (non-blocking)** — `create_all` u migracionom skriptu ne garantuje
  Alembic-građenu šemu; dodati napomenu. (gora)
- **R1 (OUT_OF_SCOPE_FINDING — eskalerirati Radovanu, NIJE blokirajući za
  kod)** — **kontradikcija u PII izvještajima.** Implementer tvrdi da
  `dentaland.db` sadrži stvarni identitet (`radovan1969@gmail.com`) koji nije
  migriran. Codex review izjavljuje da je Radovan "potvrdio brisanje 8
  ličnih zapisa + VACUUM, 0 preostalih pogodaka". **Moja read-only provera
  trenutnog `C:\Users\38765\Desktop\Dentaland\dentaland.db` pokazuje 7
  redova koji NISU očigledno sintetski**, uključujući `Milica Stojanović`
  sa email `radovan1969@gmail.com` (isto ime/email kao u implementerovom
  nalazu). Dakle ili VACUUM nije izvršen na ovoj putanji/kopiji, ili su
  podaci ponovo uneseni, ili Codex gleda drugu verziju. **Nije kodni problem**
  (task ispravno migrira samo sintetske podatke i ne dira `dentaland.db`),
  ali je PII-osjetljiva kontradikcija — potvrditi sa Radovanom prije
  bilo kakve buduće stvarne migracije. Ne uništiti informaciju.

## Verdict: PASS_WITH_NOTES

Codex-ov F1 (percent-encoded lozinka) je definitivno popravljen — regresioni
test prolazi kroz stvarni `migrations/env.py` (subprocess `alembic current`),
što sam lično potvrdio. Obim tačan (nula EXCLUDE/`btree_gist`), svi forbidden
paths netaknuti, migracioni skript arhitektonski solidan i stvarno funkcionalan
(FK-safe, read-only izvor, sequence reset, pravi integrity umjesto "nije
pukao"). Nema blokirajućih kodnih nalaza.

Jedina nota je R1 (PII kontradikcija) — to je input za Radovanov human
approval, ne za kodni verdikt. Usputni N1 je kozmetički.
