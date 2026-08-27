# DENT-IMPROVE-012 — Codex independent review

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS_WITH_NOTES
security: PASS
blocking_findings: []
```

## CILJ

Nezavisno provjeriti PostgreSQL bootstrap, Alembic konfiguraciju, jednokratni
SQLite→PostgreSQL migrator, integritet podataka i očuvanje SQLite defaulta, bez
uvođenja pravno neriješenog EXCLUDE constrainta.

Review je urađen nad eksplicitno predatim, nekomitovanim working-tree
snapshotom grane `task/DENT-IMPROVE-012-postgres-migration`.

## RE-REVIEW — FIX RUNDA 1

Prethodni F1 je **zatvoren**. `migrations/env.py` sada prije
`set_main_option` radi `_database_url.replace("%", "%%")`, čime čuva
ispravan URL nakon `ConfigParser` interpolacije.

Nova regresiona provjera nije kozmetička: percent-enkoduje znak stvarne
lozinke iz izolovanog `DATABASE_URL_TEST`, zatim u subprocessu pokreće
stvarni `alembic current`. Time prolazi kroz `migrations/env.py`, pokušava
stvarnu konekciju i potvrđuje `(head)`. Ne koristi ručno konstruisan engine
kao zamjenu za sporni put.

Nezavisno ponovljeno na portu 5433:

- ciljani `tests/test_postgres_migration.py`: **2 passed**;
- percent-encoded URL test prolazi kroz stvarni Alembic env;
- PostgreSQL overlap scenario i dalje vraća 409;
- `alembic current`: `d4e5f6a7b8c9 (head)`;
- puni suite sa `DATABASE_URL_TEST`: **376 passed**, 0 skipped;
- puni suite bez PostgreSQL env varijabli: **374 passed, 2 skipped**;
- Ruff: **All checks passed**;
- mypy: **Success**, 52 source fajla;
- agent sensors: **0 blocking findings**.

`limiter.reset()` je ograničen na novu test fixture-u i pravilno uklanja
procesno dijeljeno rate-limit stanje prije PostgreSQL HTTP scenarija. Ne
mijenja produkcijski limiter niti forbidden `test_backend.py`.

Ponovljeni scope grep nalazi `EXCLUDE`/`btree_gist` samo u backlog opisu
namjerno odgođenog rada. Nema constrainta, ekstenzije ni promjene revision
fajlova. Pravno blokirani obim ostaje netaknut.

## PRETHODNI BLOCKING FINDING — ZATVOREN U FIX RUNDI 1

### F1 — pre-fix stanje: Alembic nije prihvatao URL sa `%` escape-om

Prije fix runde, `migrations/env.py:27` je prosleđivao sirovi `DATABASE_URL` u
`config.set_main_option("sqlalchemy.url", _database_url)`. Alembicova
konfiguracija koristi `ConfigParser` interpolaciju, pa validan URL-encoded znak
u kredencijalima izaziva grešku prije pokušaja konekcije.

Nezavisna, potpuno lokalna reprodukcija bez mreže i bez stvarnih kredencijala:

```text
python -c "from alembic.config import Config; c=Config('alembic.ini');
c.set_main_option('sqlalchemy.url',
'postgresql://user:p%25word@localhost:5433/db')"

ValueError: invalid interpolation syntax in
'postgresql://user:p%25word@localhost:5433/db' at position 19
```

`%25` je normalno URL kodiranje znaka `%`; isti problem je pogađao i druge
percent-encoded dijelove URL-a. Fix runda je uradila traženi `%` → `%%`
escape i dodala regresioni test kroz stvarni `migrations/env.py`, pa ovaj
nalaz više nije aktivan.

## URAĐENO

### Scope i kritična ograničenja

- Working tree sadrži tačno prijavljene izmjene/nove fajlove:
  `backend/main.py`, `migrations/env.py`, `pyproject.toml`, backlog dokument,
  novi migracioni skript, PostgreSQL test i tri `agent_reports` fajla.
- Nema izmjena u `models.py`, `availability.py`, `migrations/versions/**`,
  `desktop/**`, `web/**` ni backup kodu.
- U diff nije uveden `EXCLUDE` constraint niti `btree_gist` ekstenzija.
- Test konekcija je prije upotrebe eksplicitno ograničena na port **5433**;
  port 5432 nije korišten.
- `.env` je gitignored i nije u statusu/diff-u; kredencijali nisu ispisivani.
- Raniji `dentaland.db` incident nije blocking finding ovog reviewa: Radovan je
  naknadno potvrdio brisanje 8 ličnih zapisa i `VACUUM`, uz 0 preostalih
  pogodaka. Implementerov izvještaj/backlog napomena o potrebi odluke je zato
  vremenski zastarjela, ali ne mijenja kodni verdict.

### PostgreSQL i migrator

- Stvarni `backend.main.get_session_factory()` sa `DATABASE_URL` iz izolovanog
  test env-a dao je `DIALECT=postgresql`, `PORT=5433`, `CONNECTED=True`.
- `pytest tests/test_postgres_migration.py -q` sa `DATABASE_URL_TEST` na 5433:
  **1 passed**; potvrđen je stvarni PostgreSQL overlap→HTTP 409 scenario.
- `alembic current` nad istom bazom: `d4e5f6a7b8c9 (head)`.
- Bez `DATABASE_URL_TEST`, puni suite daje očekivani skip umjesto pada.
- Migrator koristi FK-safe insert redoslijed
  Doctor→Service→WorkingHours→TimeOff→Appointment i obrnuti truncate;
  resetuje sekvence, poredi row/status counts i radi eksplicitne FK
  spot-checkove. SQLite izvor se otvara sa `mode=ro`.
- Napomena: PostgreSQL test direktno pravi engine i dependency override; zato
  sam test ne pokriva novi backend env bootstrap. Taj put je provjeren zasebnom
  runtime probom iznad, ali regresioni test bi bio korisniji.

### Standardna verifikacija

- `pytest tests/ -q`: **374 passed, 1 skipped**, 11 warnings.
- Projektno dokumentovana Ruff komanda koja uključuje novi skript:
  **All checks passed**.
- `mypy src/dentaland desktop backend`: **Success**, 52 source fajla.
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.
- Širi `ruff check .` pada na pet ranije postojećih nalaza u
  `scripts/coordination.py`; izmijenjeni scope i dokumentovana projektna Ruff
  komanda su čisti, pa to nije finding ovog taska.

## NE DIRATI

- Ne uvoditi EXCLUDE/btree_gist dok pravno pitanje nije riješeno.
- Ne koristiti niti testirati port 5432.
- Ne migrirati stvarne/pacijentske podatke u reviewu.
- Ne mijenjati postojeće Alembic revision fajlove radi ovog popravka.

## SLJEDEĆE

Codex re-review je **PASS**. F1 je popravljen i pokriven stvarnim Alembic
regresionim testom; svi traženi PostgreSQL i standardni gateovi su zeleni.
Snapshot sada ide Revieweru 2, zatim Radovan human approval-u. Prije toga
implementaciju i oba izvještaja treba commitovati/pushovati kao stabilan
reviewovan snapshot.
