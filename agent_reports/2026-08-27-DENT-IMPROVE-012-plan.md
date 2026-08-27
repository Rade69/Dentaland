# DENT-IMPROVE-012 — Plan (HIGH)

## OUT_OF_SCOPE_FINDING — CRITICAL CONSTRAINT triggered prije početka rada

Prije bilo kakve izmjene koda provjeren je `dentaland.db` u root-u **glavnog
repoa** (`C:\Users\38765\Desktop\Dentaland\dentaland.db`, zadnja izmjena
23.8.2026, ~40KB) — ovaj worktree ga nema kopiranog (gitignored, per-worktree
fajl), pa je provjeren read-only preko `sqlite3` URI moda (`mode=ro`, bez
pisanja/WAL fajla) direktno na putanji glavnog repoa, bez ikakve izmjene tog
fajla.

Nalaz: tabela `appointments` sadrži red sa `ime="Radovan Stojanovic"`,
`telefon="065549153"`, `email="radovan1969@gmail.com"` — ovo je stvaran
identitet (ime, telefon i email se poklapaju sa poznatim Radovanovim
kontakt podacima), ne "Test Pacijent"/`test@example.com` obrazac. Prema
Critical Constraint iz zadatka: **STAJEM**, ne kopiram ništa iz ovog fajla
u Postgres, i nastavljam ISKLJUČIVO sa potpuno sintetskim podacima koje sam
generišem za test migracionog skripta i integrity provjere.

Posljedica na obim: `scripts/migrate_sqlite_to_postgres.py` prima
`--source-db`/`--target-url` parametre generički (radi za bilo koji izvor),
ali će biti STVARNO pokrenut/testiran u ovom tasku samo nad SVJEŽE
generisanom sintetskom SQLite bazom (napravljenom u ovom worktree-u, npr.
`scripts/seed_synthetic_sqlite.py` ili inline u testu), nikad nad
`C:\Users\38765\Desktop\Dentaland\dentaland.db`. Ovaj nalaz ide u finalni
izvještaj i treba eskalirati Radovanu (van scope-a implementera da odluči
šta se radi sa tim fajlom — brisanje, anonimizacija ili ostavljanje kao
lokalni dev artefakt).

## Cilj

Omogućiti `backend/main.py` da radi nad PostgreSQL bazom kroz `DATABASE_URL`
env var (default ostaje SQLite/`DENTALAND_DB_PATH`, nepromijenjeno), dokazati
da `alembic upgrade head` čisto gradi šemu na praznoj Postgres bazi, napisati
jednokratan migracioni skript SQLite→Postgres testiran na sintetskim
podacima sa integrity provjerom, i potvrditi da `validate_appointment_overlap`
i dalje baca `OverlapError`→409 nad Postgres konekcijom. Bez EXCLUDE/
btree_gist bilo gdje.

## Pogođeno (allowed paths, iz Task Contracta)

- `backend/main.py` — `_build_session_factory`/`get_session_factory`: grana
  na `DATABASE_URL` ako je postavljen, inače postojeće SQLite ponašanje.
- `pyproject.toml` — dodati `psycopg2-binary` (već instaliran globalno u
  aktivnom Python 3.14 okruženju, `postgresql://` URL format iz `.env`
  odgovara psycopg2 default dijalektu bez URL prefiksa — ne zahtijeva
  promjenu `.env` formata). Alternativa `psycopg[binary]` (v3) razmotrena
  i odbačena — vidi "Odbačene opcije".
- `migrations/env.py` — `DATABASE_URL` override prije `engine_from_config`
  (standardni Alembic obrazac), `alembic.ini` default netaknut.
- `scripts/migrate_sqlite_to_postgres.py` (novo) — FK-safe kopiranje
  (doctors → services → working_hours/time_off/appointments), TZDateTime
  vrijednosti kao UTC-aware, integrity izvještaj (row count + spot-check FK
  + spot-check status vrijednosti).
- `tests/test_postgres_migration.py` (novo, opciono) — ili ručna evidencija
  u izvještaju ako Postgres test infrastruktura traži previše vremena za
  ugraditi u pytest suite bez diranja `conftest.py` van dozvoljenih putanja.
- `agent_reports/**` — ovaj plan + finalni izvještaj.
- `docs/DENTALAND_IMPROVEMENT_BACKLOG.md` — samo status napomena na kraju
  sekcije 13 (bez mijenjanja opisa obima).

## Plan (koraci)

1. Dodati `psycopg2-binary` u `pyproject.toml` dependencies.
2. `backend/main.py`: `_build_session_factory` prima URL (ne samo
   `db_path`); `get_session_factory` čita `DATABASE_URL` prvo, pa fallback
   na postojeći `DENTALAND_DB_PATH` → `sqlite:///{db_path}` obrazac
   nepromijenjen.
3. `migrations/env.py`: `config.set_main_option("sqlalchemy.url", db_url)`
   ako je `os.environ.get("DATABASE_URL")` postavljen, prije
   `engine_from_config` poziva u `run_migrations_online` (offline grana
   ostaje netaknuta osim istog override-a radi konzistentnosti).
4. Ručno postaviti `DATABASE_URL_TEST` iz `.env` u shell i pokrenuti
   `alembic upgrade head` na praznoj `dentaland_test` bazi — snimiti pun
   output kao evidence. Uporediti rezultujuću šemu (`\d` per tabela ili
   `information_schema` upit) sa SQLite šemom (kolone, tipovi, enum/CHECK
   vrijednosti za `appointment_status`).
5. Napisati `scripts/migrate_sqlite_to_postgres.py`: CLI sa
   `--source-sqlite`/`--target-url`/`--dry-run` (ili sličnim), FK-safe red
   insertovanja, eksplicitna konverzija SQLite naivnih/UTC stringova u
   `datetime` sa `tzinfo=UTC` prije upisa (SQLAlchemy `TZDateTime` tip radi
   ostatak), integrity report na kraju (row count po tabeli, FK spot-check,
   status vrijednosti spot-check).
6. Generisati potpuno sintetsku SQLite bazu (svježa, u
   `scripts/seed_synthetic_sqlite.py` ili inline u testu/privremenom
   skriptu van git trackinga) — 3 doktora, par usluga, par termina sa
   izmišljenim imenima ("Test Pacijent 1" i sl., NE stvarni podaci) —
   pokrenuti migracioni skript protiv nje i protiv prazne
   `dentaland_test` Postgres baze, snimiti integrity izvještaj.
7. Test overlap zaštite nad Postgres: iskoristiti isti scenario kao
   `test_confirm_preklapanje_vraca_409` iz `tests/test_backend.py`, ali sa
   engine-om koji gađa `DATABASE_URL_TEST` (Postgres) umjesto SQLite
   in-memory — ili novi parametrizovan test u
   `tests/test_postgres_migration.py`, ili ručni scenario dokumentovan u
   izvještaju ako parametrizacija postojećeg testa nosi rizik da pokvari
   CI koji možda nema Postgres dostupan (odluka pada tokom implementacije,
   dokumentovaće se u finalnom izvještaju).
8. `ruff check` / `mypy` / `pytest tests/ -q` (bez `DATABASE_URL` postavljenog)
   moraju ostati čisti — potvrđuje da default SQLite put nije pokvaren.
9. Provjeriti `git status` prije završetka da `.env`/kredencijali nisu u
   diff-u.

## Šta NE dirati

`desktop/**`, `src/dentaland/models.py`, `src/dentaland/services/availability.py`,
`src/dentaland/backup.py`, `src/dentaland/backup_cli.py`,
`migrations/versions/**` (postojeći fajlovi), `web/**`. Nema EXCLUDE/
btree_gist reference bilo gdje. Ne diram Windows `postgresql-16` servis na
portu 5432 (`deklarant_pro`) — sve komande eksplicitno ciljaju port 5433.
Ne kopiram `C:\Users\38765\Desktop\Dentaland\dentaland.db` u Postgres (vidi
OUT_OF_SCOPE_FINDING gore).

## Plan verifikacije

- `alembic upgrade head` na praznoj `dentaland_test` — pun output kao
  evidence.
- Row-count i schema-diff tabela SQLite (sintetski izvor) vs Postgres
  (odredište) u finalnom izvještaju.
- `pytest tests/ -q` bez `DATABASE_URL` (mora ostati identično baseline-u).
- Poseban test/scenario koji dokazuje `OverlapError`→409 nad Postgres
  konekcijom.
- `ruff check .` i `mypy src/dentaland backend` čisti (baseline
  poređenje — ne uvoditi nove greške).
- `git status --short` prije predaje — potvrda da `.env` nije staged/u
  diff-u.

## Rollback

Sve promjene su aditivne i granaju se na prisustvo `DATABASE_URL`:
uklanjanjem/nepostavljanjem te env varijable, `backend/main.py` i
`migrations/env.py` se ponašaju identično kao prije taska (SQLite,
`DENTALAND_DB_PATH`). SQLite fajl (`dentaland.db`) se nikad ne briše ni
premješta u ovom tasku — migracioni skript samo čita iz njega (kad bi se
ikad pokrenuo nad njim, što se u ovom tasku eksplicitno NE radi zbog
CRITICAL CONSTRAINT nalaza) i piše u Postgres, izvor ostaje netaknut.
Ako Postgres grana treba da se ukloni u potpunosti: revert commita na ovoj
grani prije merge-a (grana se još nije mergovala u `main`).

## Odbačene opcije

- **`psycopg[binary]` (psycopg3)** umjesto `psycopg2-binary` — odbačeno jer
  bi zahtijevalo `postgresql+psycopg://` prefiks u `DATABASE_URL` (`.env`
  već ima plain `postgresql://`, mijenjanje tog formata nije u dozvoljenim
  putanjama za `.env` i nepotrebno usložnjava evidence/reproduction korake
  za reviewera). `psycopg2-binary` je već instaliran u aktivnom okruženju i
  SQLAlchemy 2.0 ga bira kao default dijalekt za plain `postgresql://` URL.
- **Dodavanje `python-dotenv` da se `.env` čita automatski** — odbačeno,
  van obima ovog taska i nekonzistentno sa postojećim obrascem
  (`.env.example` eksplicitno kaže "aplikacija NE čita `.env` fajl
  automatski" za SMTP varijable) — `DATABASE_URL` se postavlja isto ručno,
  kao i ostale env varijable u projektu.
- **Parametrizacija cijelog `tests/test_backend.py` na dva dijalekta preko
  fixture-a** — razmotreno, ali potencijalno predstavlja veći dijametar
  izmjene postojećeg fajla nego što je potrebno; umjesto toga dodaje se
  fokusiran novi test/fajl koji cilja samo overlap-scenario nad Postgres,
  postojeći SQLite testovi ostaju netaknuti (manji diff, manji rizik da
  se nešto od postojećeg pokvari).
