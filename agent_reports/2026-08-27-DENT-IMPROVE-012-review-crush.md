---
task_id: DENT-IMPROVE-012
risk: HIGH
reviewer: crush
role: Reviewer 2 (nezavisna provjera, fresh)
verdict: PASS_WITH_NOTES
date: 2026-08-27
---

# DENT-IMPROVE-012 — Crush nezavisan review

Nezavisan pregled od nule. Nisam čitao Codex/Pi rezonovanje prije sopstvene
analize koda i verifikacija — njihove izvještaje sam pročitao tek nakon što
sam sam pregledao diff i pokrenuo sve gateove.

## Verdikt

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## Nalaz

### N1 (non-blocking, novi nalaz) — bezuslovni `DATABASE_URL` override kvari 4 SQLite-migraciona testa i može downgrade-ovati bazu na koju URL pokazuje

- Lokacija: `migrations/env.py:27-28` — `_database_url = os.environ.get("DATABASE_URL")` → `config.set_main_option("sqlalchemy.url", _database_url.replace("%", "%%"))` **bezuslovno**, bez provjere da li pozivalac već ima postavljenu vrijednost.
- Posljedica: 4 postojeća testa koriste `Config("alembic.ini")` + `config.set_main_option("sqlalchemy.url", "sqlite:///...")` + `command.upgrade/downgrade` (`test_models.py:74, :274, :294`; `test_requests.py:237`). Kada je `DATABASE_URL` postavljen u okruženju, env.py **pregazi** njihov SQLite URL, pa Alembic migrira/downgrade-uje **Postgres bazu na koju `DATABASE_URL` pokazuje** umjesto izolovane SQLite tmp baze.
- Reprodukovano lično (nezavisno): `pytest tests/ -q` sa `DATABASE_URL` (i `DATABASE_URL_TEST`) postavljenim → **4 failed, 372 passed**:
  - `tests/test_models.py::test_alembic_migracija_ima_status_constraint_i_manual_override_default`
  - `tests/test_models.py::test_alembic_migracija_dodaje_confirmed_arrived_at`
  - `tests/test_models.py::test_alembic_migracija_cuva_postojece_termine_pri_upgrade_i_downgrade`
  - `tests/test_requests.py::test_migracija_dozvoljava_pending_bez_doktora`
  Isti suite sa **samo** `DATABASE_URL_TEST` (bez `DATABASE_URL`) → **376 passed, 0 skipped**.
- Ozbljnost (zašto nije čisto kozmetički): `test_migracija_cuva_postojece_termine_pri_upgrade_i_downgrade` radi `command.upgrade(config, "b2c3d4e5f6a7")` pa `command.upgrade(config, "head")`; kad env.py otme URL na Postgres, to je stvarni **downgrade→upgrade ciklus nad Postgres bazom**, ne nad tmp SQLite fajlom — može obrisati podatke. U mom run-u `dentaland_test` je izgubio sintetske redove koje je implementer ostavio kao inspektabilan artefakt (sa 6/3/15/2 na 1/6/1/0 appointments/doctors/working_hours/time_off).
- Zašto **ne blokira** ovaj task: (a) Task Contract eksplicitno traži "standardni Alembic env var override — env var ima prednost nad `alembic.ini`" — implementacija je tačno taj obrazac; (b) acceptance criteria "bez `DATABASE_URL` ponašanje identično" je zadovoljeno (374 passed, 2 skipped); (c) Faza 0 ne postavlja `DATABASE_URL` globalno, pa nema sadašnjeg produkcionog rizika.
- Preporuka (za Fazu 1, ne sada): ili (i) env.py poštuje već postavljenu `sqlalchemy.url` (`if not config.get_main_option("sqlalchemy.url"): set_main_option(...)`), ili (ii) SQLite-migracioni testovi se skipuju/izoluju kad je `DATABASE_URL` postavljen. Ovo treba zabilježiti kao budući task, ne dirati u ovom review-u.

## Šta je verifikovano lično (ne iz izvještaja)

Sve komande pokrenute u worktree-u `task/DENT-IMPROVE-012-postgres-migration`.

| Provjera | Rezultat |
|---|---|
| `git diff --name-only` (tracked) | samo `backend/main.py`, `migrations/env.py`, `pyproject.toml`, `docs/DENTALAND_IMPROVEMENT_BACKLOG.md` |
| forbidden paths (`models.py`, `availability.py`, `desktop/**`, `web/**`, `migrations/versions/**`, `backup.py`, `backup_cli.py`, `alembic.ini`) | **netaknuti** (prazan diff/status) |
| `EXCLUDE`/`btree_gist` grep cijelog diff-a | samo u backlog komentaru "namjerno NIJE dio ove implementacije" — nula u kodu/šemi |
| `.env` | gitignored (`git check-ignore` → jeste), nije u diff/status |
| PostgreSQL instanca (port 5433) | running, PID 8076 (`pg_ctl status`) |
| `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py scripts/migrate_sqlite_to_postgres.py` | **All checks passed** |
| `mypy src/dentaland desktop backend` | **Success: no issues found in 52 source files** |
| `python scripts/agent_sensors.py --all` | **0 blocking findings** |
| `pytest tests/ -q` (bez `DATABASE_URL`) | **374 passed, 2 skipped** (2 nova Postgres testa preskočena) |
| `pytest tests/ -q` (samo `DATABASE_URL_TEST`) | **376 passed, 0 skipped** |
| `pytest tests/test_postgres_migration.py -q` (izolovano) | **2 passed** (409 conflict + percent-encoded F1 regresija) |
| `alembic current` nad Postgres | `d4e5f6a7b8c9 (head)`, `Context impl PostgresqlImpl` |
| migracioni skript `--dry-run` nad svježom sintetskom SQLite bazom | čist integrity report: doctors=2, services=1, working_hours=1, time_off=1, appointments=1 |

## Potvrđeno čitanjem koda (nije runtime-duplirano)

- `scripts/migrate_sqlite_to_postgres.py`: FK-safe redoslijed `_MODELS_IN_ORDER = [Doctor, Service, WorkingHours, TimeOff, Appointment]` (roditelji prije djece); izvor `sqlite:///file:{path}?mode=ro&uri=true` (read-only); integrity nije površna — `_fk_spot_check` (`NOT EXISTS` nad `working_hours.doctor_id`, `time_off.doctor_id`, `appointments.doctor_id`, `appointments.service_id`) + `_status_counts` (status po vrijednosti) + row count, ne samo "insert nije pukao"; `_reset_sequences` (`setval` po tabeli) za Postgres serial.
- `backend/main.py`: `DATABASE_URL` ima prednost, else identičan SQLite (`DENTALAND_DB_PATH` → `sqlite:///{db_path}`). Aditivno, ne mijenja default.
- `pyproject.toml`: dodan samo `psycopg2-binary>=2.9` (izbor dokumentovan).
- `tests/test_postgres_migration.py`: `pytestmark = skipif(not DATABASE_URL_TEST)` — čisto skipuje bez Postgres instance; F1 regresioni test ide kroz stvarni `migrations/env.py` (subprocess `alembic current`), ne ručni engine.

## Napomena o stanju test baze

`dentaland_test` (port 5433, izolovana) je test/disposable baza. Moje pokretanje suite-a (uključujući i gornji run sa `DATABASE_URL` koji je reprodukovao N1) izmijenilo je sintetske redove u njoj — trenutno stanje appointments=1, doctors=6, services=3, working_hours=1, time_off=0, `alembic_version`=head. Ovo je očekivan efekat testova nad test bazom i ne utiče na kodni verdikt; baza se po potrebi drop/recreate. Ne sadrži stvarne podatke.

## CILJ / URAĐENO / NE DIRATI / SLJEDEĆE

```text
CILJ: SQLite→PostgreSQL migracija (DATABASE_URL konekcija + Alembic + jednokratni skript + 409 potvrda), bez EXCLUDE/btree_gist.
URAĐENO: PASS_WITH_NOTES — scope/acceptance/architecture/security čisti; jedan non-blocking N1 (bezuslovni DATABASE_URL override) za Fazu 1.
NE DIRATI: EXCLUDE/btree_gist; port 5432; stvarne pacijentske podatke; desktop/models/availability/backup/migrations/versions.
SLJEDEĆE: Radovan human approval. Zabilježiti N1 kao budući Faza-1 task (SQLite-migracioni testovi vs globalni DATABASE_URL).
```
