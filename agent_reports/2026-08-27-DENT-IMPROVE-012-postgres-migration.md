---
task_id: DENT-IMPROVE-012
risk: HIGH
implementer: claude
status: "Fix runda 2 (Pi re-review nalaz) završena — vidi 'Fix runda 2' sekciju. Čeka re-review Pi/Codex i Crush, pa human approval."
date: 2026-08-27
---

## Fix runda 2 (Pi re-review, koristeći review-code/verify-before-complete skills) — pravi regresija, popravljena

**Nalaz (Pi, HIGH):** `migrations/env.py`-ov `DATABASE_URL` override je bio
**bezuslovan** — pregazio bi `sqlalchemy.url` čak i kad je pozivalac
(postojeći `tests/test_models.py`/`test_requests.py`, koji programski prave
sopstveni `Config("alembic.ini")` i eksplicitno postave URL na izolovanu
`tmp_path` SQLite bazu PRIJE `command.upgrade(config, ...)`) već eksplicitno
odabrao drugačiju metu. Kad je proces imao `DATABASE_URL` u okruženju
(npr. i `DATABASE_URL_TEST` iz `.env`, ako se oboje izvezu zajedno — prirodan
scenario), Alembic bi tiho migrirao na Postgres umjesto na testovu
namjeravanu SQLite bazu, a test bi zatim pao sa `NoSuchTableError` gledajući
praznu SQLite datoteku. Pogođena 4 PRETHODNO POSTOJEĆA testa:
`test_alembic_migracija_ima_status_constraint_i_manual_override_default`,
`test_alembic_migracija_dodaje_confirmed_arrived_at`,
`test_migracija_cuva_postojece_termine_pri_upgrade_i_downgrade`,
`test_requests.py::test_migracija_dozvoljava_pending_bez_doktora`.

**Zašto ranija verifikacija (Fix runda 1, Codex PASS, Pi prvi PASS_WITH_NOTES)
ovo nije uhvatila:** svi ranije navedeni "puni suite" pokretanja su izvozila
SAMO `DATABASE_URL_TEST` (za `test_postgres_migration.py`-ov sopstveni
engine), NIKAD `DATABASE_URL` istovremeno — taj TAČAN kombinovan scenario
(oba env varijabla postavljena istovremeno u istom procesu, prirodno
očekivano stanje ako neko `source .env` ili CI izveze cijeli fajl) nikad nije
bio stvarno testiran prije ovog Pi prolaza. Ovo je razlog zašto raniji
"376 passed" izvještaji nisu bili netačni ZA MJERENI uslov, ali JESU bili
nepotpuni za realan uslov koji je Pi ispravno pretpostavio i reprodukovao.

**Fix:** override u `migrations/env.py` se sad primjenjuje SAMO ako je
`config.get_main_option("sqlalchemy.url")` i dalje jednak neizmijenjenom
`alembic.ini` defaultu (`sqlite:///dentaland.db`) — ako je pozivalac već
eksplicitno postavio drugačiji URL (kao ova 4 testa), taj izbor se poštuje.
Ne dira se nijedan test fajl (van `allowed_paths` za ovaj task) — cijeli fix
ostaje u `migrations/env.py`.

**Nezavisno reprodukovano LIČNO, prije i poslije fixa:**
- Prije fixa, sa `DATABASE_URL` stvarno postavljenim (ne samo
  `DATABASE_URL_TEST`): sva 4 testa padaju sa `NoSuchTableError: appointments`,
  stderr potvrđuje `Context impl PostgresqlImpl` — dokaz da je Alembic
  stvarno otišao na Postgres umjesto SQLite.
- Poslije fixa: ista 4 testa → **4 passed**. `test_postgres_migration.py`
  (F1 regresija + 409 test) i dalje → **2 passed** (fix ne kvari namjeravanu
  upotrebu env varijable). Cijeli `pytest tests/ -q` sa OBJE env varijable
  postavljene istovremeno → **376 passed, 0 failed** (prvi put stvarno
  testiran taj kombinovan uslov). Bez ijedne env varijable → **374 passed,
  2 skipped** (nepromijenjeno). `ruff`/`mypy` (52 fajla)/`agent_sensors.py
  --all` → svi čisti.

## Post-review addendum (27.8.2026) — N1 i R1 riješeni

**N1 (Pi, kozmetički)** — dodata napomena u docstring
`scripts/migrate_sqlite_to_postgres.py` (`run_migration`) da
`Base.metadata.create_all` ne garantuje da je šema stvarno građena kroz
Alembic — skript pretpostavlja da je `alembic upgrade head` već autoritet,
ne koristi se kao zamjena za njega. `ruff`/`mypy` ponovo potvrđeni čisti
nakon izmjene.

**R1 (Pi, OUT_OF_SCOPE_FINDING, PII)** — eskalirano Radovanu direktno (ne
sahranjeno u izvještaju). Razjašnjeno da nije stvarna kontradikcija: raniji
"8 obrisanih, 0 pogodaka" se odnosio isključivo na tačan identitet
(`Radovan Stojanovic`/`065549153`/`radovan1969@gmail.com`), dok su
preostali redovi (Nikola, Sanja, Predrag, Vladan, Milan Stojanović/Krunić,
i "Milica Stojanović" koja dijeli Radovanov email ali drugo ime) bili
namjerno neobrisani do eksplicitne Radovanove odluke. Radovan je odlučio:
obrisati i njih. Izvršeno — 6 preostalih ne-sintetskih redova (ID 4, 19,
24, 25, 26, 27) obrisano iz `C:\Users\38765\Desktop\Dentaland\dentaland.db`
i `VACUUM` pokrenut. Provjereno: preostalo 10 redova, svi očigledno
sintetski ("Test Layout" x8, "Jon Stewart Doe", "João Souza Silva" —
`test@example.com`/`.us` email domeni). Ovaj fajl NIJE i NIKAD nije bio dio
ovog taska (glavni repo, ne worktree; migracioni skript ga nikad nije
dirao) — čisto lokalni dev artefakt, izmjena je van git trackinga
(`*.db` gitignored).

---

## Fix runda 1 (Codex review, `2026-08-27-DENT-IMPROVE-012-review-codex.md`, verdict REJECT)

**F1 (HIGH, blocking) — popravljeno.** `migrations/env.py` je prosljeđivao
sirovi `DATABASE_URL` u `Config.set_main_option`, čiji `ConfigParser` radi
interpolaciju — validan URL-encoded znak u kredencijalima (npr. `%25` u
lozinci) je pucao (`ValueError: invalid interpolation syntax`) PRIJE
ijednog pokušaja konekcije. Nezavisno reprodukovano (Codex-ov tačan
repro-scenario, potvrđeno LIČNO prije fixa) i popravljeno standardnim
Alembic obrascem: `_database_url.replace("%", "%%")` prije
`set_main_option` — potvrđeno da se ispravno vraća kroz i `get_main_option`
(offline mod) i `get_section` (online mod/`engine_from_config`).

Dodat regresioni test `tests/test_postgres_migration.py::
test_alembic_database_url_sa_percent_encoded_lozinkom` — ide kroz STVARAN
`migrations/env.py` (subprocess `alembic current`, ne ručno konstruisan
`Config`/engine, tačno kako je Codex tražio), percent-enkoduje prvi znak
STVARNE lozinke iz `DATABASE_URL_TEST` (SQLAlchemy/psycopg2 je ispravno
dekoduju nazad, konekcija stvarno uspijeva). Potvrđeno da test PADA bez
fixa (privremeno vraćen stari kod, test failed, fix vraćen) i PROLAZI sa
fixom — ovo je stvarna regresiona zaštita, ne kozmetički test.

**Usput otkriven i popravljen drugi problem** (nije bio u Codex reviewu,
otkriven dok sam sam pokretao pun `pytest tests/ -q` suite nakon dodavanja
novog testa): `test_confirm_preklapanje_vraca_409_nad_postgres` je
povremeno padao sa `429 Too Many Requests` kad se pokreće KAO DIO cijelog
suite-a (ne izolovano) — uzrok je `slowapi` `Limiter` (backend/main.py) koji
je proces-singleton in-memory storage bez reseta između testova, ključan
po `get_remote_address` koji je za `TestClient` uvijek isti ("testclient").
`tests/test_backend.py::test_rate_limit_na_submit_endpointu` namjerno troši
tu kvotu (šalje 11 zahtjeva), i taj test je zato u postojećem kodu
POSTAVLJEN POSLJEDNJI među testovima koji gađaju taj endpoint u tom fajlu
— implicitan, nezapisan invarijant na koji je moj novi test (u DRUGOM
fajlu, koji pytest učitava poslije `test_backend.py` po abecedi) naletio.
Rješenje: `limiter.reset()` na početku `client` fixture-a u
`test_postgres_migration.py`, izoluje ovaj test od dijeljenog stanja bez
diranja `test_backend.py` (forbidden path/van scope-a ovog taska). Nije
Postgres-specifičan bug niti regresija u aplikacionom kodu — čisto
test-izolacioni artefakt otkriven dodavanjem novog testa u novi fajl.

Verifikacija nakon oba fixa:
- `pytest tests/ -q` SA `DATABASE_URL_TEST` postavljenim → **376 passed**,
  0 failed, 0 skipped (374 prethodni baseline + 2 nova Postgres testa).
- `pytest tests/ -q` BEZ `DATABASE_URL_TEST` → **374 passed, 2 skipped**
  (oba nova Postgres testa se čisto preskaču) — identično baseline broju
  `passed` prije taska.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py
  scripts/migrate_sqlite_to_postgres.py` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success, 52 source files**
  (ispravljena i moja ranija greška u komandi koja je izostavila `desktop`).
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.
- `git status --short` → `.env` nije u diff-u (provjereno ponovo).

# DENT-IMPROVE-012 — SQLite→PostgreSQL migracija — Finalni izvještaj

## ⚠️ OUT_OF_SCOPE_FINDING — ESKALIRATI RADOVANU (pročitati prije ostatka izvještaja)

Prije bilo kakve izmjene koda (u prethodnoj sesiji, prenosim ovdje jer je
kritično za odluku o daljim koracima) provjeren je
`C:\Users\38765\Desktop\Dentaland\dentaland.db` (glavni repo, **ne** ovaj
worktree — ovaj worktree ga nema kopiranog, per-worktree fajl je
gitignored). Provjera je urađena READ-ONLY preko SQLite URI moda
(`mode=ro`), bez pisanja/WAL fajla, direktno na putanji glavnog repoa.

**Nalaz:** tabela `appointments` sadrži red sa `ime="Radovan Stojanovic"`,
`telefon="065549153"`, `email="radovan1969@gmail.com"` — ovo je stvaran
identitet (ime, telefon i email se poklapaju sa poznatim Radovanovim
kontakt podacima), ne sintetski "Test Pacijent"/`test@example.com` obrazac.

**Odluka (već primijenjena, ne mijenjana u ovoj sesiji):** prema Critical
Constraint iz Task Contracta ("Nikad ne migrirati direktno na
produkcijskim/stvarnim pacijentskim podacima... implementer STAJE i
prijavljuje kao OUT_OF_SCOPE_FINDING"), **ništa iz tog fajla nije nikad
kopirano u Postgres**. Cijela implementacija (migracioni skript, integrity
provjera, overlap test) je urađena i testirana isključivo nad
**potpuno sintetskom** SQLite bazom generisanom u ovoj sesiji (izmišljena
imena "Test Doktor N"/"Test Pacijent N", nikad stvarni podaci).

**Šta ostaje za Radovana da odluči** (van scope-a/ovlaštenja implementera):
šta se radi sa `C:\Users\38765\Desktop\Dentaland\dentaland.db` — brisanje,
anonimizacija tog jednog reda, ili svjesno zadržavanje kao lokalni dev
artefakt uz svijest o riziku. Ovaj task ga nije dirao niti će ga dirati.

---

## Šta je urađeno u ovoj sesiji (koraci 5-9 iz plana)

Prethodna sesija (prekinuta) je već završila korake 1-4: `DATABASE_URL`
podrška u `backend/main.py`, override u `migrations/env.py`,
`psycopg2-binary` u `pyproject.toml`, i `alembic upgrade head` na praznoj
`dentaland_test`. Sve provjereno diff-om na početku ove sesije i potvrđeno
netaknuto/tačno kao opisano.

Ova sesija je uradila:

1. **`scripts/migrate_sqlite_to_postgres.py`** (novo, tracked) — CLI sa
   `--source-sqlite`/`--target-url`/`--truncate-target`/`--dry-run`.
   FK-safe redoslijed insertovanja (`doctors → services → working_hours,
   time_off, appointments`), rad na Core (Table) nivou — ne kroz ORM
   identity map, da se izbjegnu problemi vezanja objekta za dvije sesije
   istovremeno. Izvor se otvara isključivo `mode=ro` (potvrđeno testom da
   pokušaj pisanja baca `OperationalError`). Nakon kopiranja resetuje
   Postgres sekvence (`setval(pg_get_serial_sequence(...))`, sigurno i za
   praznu tabelu) i radi FK spot-check + status-vrijednost spot-check
   (ne samo "insert nije pukao").
2. **Sintetska SQLite baza** — generisana privremenim skriptom **van git
   trackinga** (scratchpad, ne u worktree-u — vidi "Odbačene opcije" niže
   zašto nije `scripts/seed_synthetic_sqlite.py`): 3 doktora ("Test Doktor
   1/2/3"), 3 usluge, 15 working_hours redova, 2 time_off, 6 appointments
   (po jedan za svaki od 6 status vrijednosti: SCHEDULED, PENDING,
   CANCELLED, COMPLETED, NO_SHOW, REJECTED), sva imena/telefoni/email-ovi
   izmišljeni (`Test Pacijent N`, `test.pacijentN@example.com`).
3. Migracija pokrenuta protiv `dentaland_test` (uz `--truncate-target` da
   poređenje bude tačno) — integrity report čist, vidi tabelu ispod.
4. **`tests/test_postgres_migration.py`** (novo, tracked, opciono po
   kontraktu — odabrano kao automatizovan test, ne samo ručna evidencija,
   vidi "Odbačene opcije") — isti scenario kao
   `tests/test_backend.py::test_confirm_preklapanje_vraca_409`, ali sa
   `sessionmaker` vezanim za `DATABASE_URL_TEST` (Postgres) umjesto SQLite
   in-memory. `pytest.mark.skipif` na odsustvo `DATABASE_URL_TEST` — bez
   nje se test PRESKAČE, ne puca, pa standardan `pytest tests/ -q` bez
   Postgres instance ostaje netaknut. Čisti za sobom svoje redove
   (naziv/ime marker `"... Postgres Overlap Test"`, brisanje i na ulazu i
   na izlazu fixture-a — otporno i na prethodni pukli run).
5. Verifikacije (detalji niže): `pytest tests/ -q` (bez `DATABASE_URL`),
   `ruff check`, `mypy src/dentaland backend` — svi čisti, baseline
   nepromijenjen.
6. `docs/DENTALAND_IMPROVEMENT_BACKLOG.md` — dodana status napomena na
   kraju sekcije 13 (bez izmjene opisa obima).
7. Obrisan stray `.tmp_alembic_output.txt` (nepotpuna evidenca iz
   prekinute sesije), zamijenjen punim, čistim `alembic upgrade head`
   izlazom u ovom izvještaju.
8. `git status --short` potvrđuje da `.env` nije u diff-u/staged (vidi
   ispod).

## Required evidence

### 1. Migration dry-run izlaz (`alembic upgrade head` na `dentaland_test`)

Baza je već bila na `head` iz prethodne sesije; ponovljeno pokretanje
(`DATABASE_URL=<DATABASE_URL_TEST> alembic upgrade head`) daje čist,
kompletan izlaz bez ijedne greške — potvrđuje idempotentnost i da je šema
i dalje na `head` (`alembic current` → `d4e5f6a7b8c9 (head)`):

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

Dodatno, radi potvrde da Alembic **replay od nule** ispravno gradi šemu
(ne samo da je stara evidencija bila tačna), migracija je pokrenuta i na
svježoj SQLite bazi (`sqlite:///<scratch>/schema_check.db`) — svih 4
revizija (`a1b2c3d4e5f6 → b2c3d4e5f6a7 → c3d4e5f6a7b8 → d4e5f6a7b8c9`)
primijenjeno bez greške, uključujući sve 3 `batch_alter_table` migracije
(SQLite-specifičan obrazac). Ova SQLite baza je korištena kao referentna
tačka za schema-diff ispod (ne stvaran `dentaland.db`).

### 2. Schema-diff potvrda (SQLite vs Postgres)

Kolone, tipovi i nullable-flag upoređeni za svih 5 tabela
(`doctors, services, working_hours, time_off, appointments`) preko
`PRAGMA table_info` (SQLite) i `information_schema.columns` (Postgres).
**Svih 26 kolona podudarno** — nema nedostajućih/viška kolona, nema
nullable neslaganja. Tipovi se razlikuju samo u dijalekt-specifičnoj
notaciji (očekivano i bezopasno: `INTEGER`↔`integer`, `DATETIME`↔`timestamp
without time zone`, `VARCHAR(n)`↔`character varying`, `BOOLEAN`↔`boolean`,
`TIME`↔`time without time zone`, `DATE`↔`date`, `TEXT`↔`text`).

`status` enum (`Enum(..., native_enum=False)` u modelu → CHECK
constraint, ne Postgres native enum tip, namjerno, isti obrazac na oba
dijalekta):

- SQLite: `CONSTRAINT appointment_status CHECK (status IN ('SCHEDULED', 'CANCELLED', 'COMPLETED', 'NO_SHOW', 'PENDING', 'REJECTED'))`
- Postgres: `CHECK (((status)::text = ANY (ARRAY[('SCHEDULED'::character varying)::text, ('CANCELLED'::character varying)::text, ('COMPLETED'::character varying)::text, ('NO_SHOW'::character varying)::text, ('PENDING'::character varying)::text, ('REJECTED'::character varying)::text])))`

Identičnih 6 vrijednosti, isti redoslijed. Potvrđeno da nema
`EXCLUDE`/`btree_gist`/gist-indeksa nigdje u Postgres šemi (provjereno
preko `pg_constraint` — jedini constraint tipa `c` na `appointments` je
gornji CHECK).

### 3. Row count comparison (sintetski izvor vs Postgres odredište)

Migracioni skript pokrenut: `python scripts/migrate_sqlite_to_postgres.py
--source-sqlite <sintetski.db> --target-url <DATABASE_URL_TEST>
--truncate-target`. Pun izlaz:

```text
=== Integrity report ===
table             source_count  target_count  status
doctors           3             3             OK
services          3             3             OK
working_hours     15            15            OK
time_off          2             2             OK
appointments      6             6             OK
    status counts (source): {'CANCELLED': 1, 'COMPLETED': 1, 'NO_SHOW': 1, 'PENDING': 1, 'REJECTED': 1, 'SCHEDULED': 1}
    status counts (target): {'SCHEDULED': 1, 'NO_SHOW': 1, 'PENDING': 1, 'REJECTED': 1, 'COMPLETED': 1, 'CANCELLED': 1}

Overall: OK
```

FK spot-check (ugrađen u skript, provjerava `working_hours.doctor_id`,
`time_off.doctor_id`, `appointments.doctor_id`, `appointments.service_id`
protiv roditeljskih tabela preko `NOT EXISTS`) nije prijavio nijednu
orphan referencu — nema `FK VIOLATION` linija u izlazu iznad.

Dodatno provjereno (sekvenca): nakon migracije, novi `INSERT` preko ORM-a
dobija `id=4` za doctors (bez PK kolizije sa migriranim ID-jevima 1-3) —
potvrđuje da `setval()` reset radi ispravno.

Napomena: `dentaland_test` trenutno sadrži ovih 6+3+3+15+2 sintetska reda
kao artefakt ovog testa (nije obrisano nakon evidence-run-a — namjerno,
radi reproducibilnosti za reviewera; sve je sintetski test podatak u
izolovanoj test bazi, ne nešto što treba tajiti).

### 4. Conflict test rezultat (409 nad Postgres)

`tests/test_postgres_migration.py::test_confirm_preklapanje_vraca_409_nad_postgres`
— isti scenario kao postojeći
`tests/test_backend.py::test_confirm_preklapanje_vraca_409`
(potvrđivanje 30-minutnog preklapanja termina za istog doktora), ali sa
`get_session_factory` override-om koji gađa `DATABASE_URL_TEST` (Postgres)
umjesto SQLite in-memory. `validate_appointment_overlap`
(`src/dentaland/services/availability.py`, nedirano, forbidden path) i
dalje baca `OverlapError` koji se mapira u HTTP 409 — potvrđeno da ista
aplikaciona logika radi nepromijenjeno na Postgres dijalektu.

```text
tests/test_postgres_migration.py::test_confirm_preklapanje_vraca_409_nad_postgres PASSED
1 passed, 2 warnings in 3.16s
```

Test je odabran kao **automatizovan**, ne samo ručna evidencija (plan je
ostavio odluku implementeru) — razlog: `pytest.mark.skipif` na odsustvo
`DATABASE_URL_TEST` čini ga bezopasnim za CI/okruženja bez Postgres
(potvrđeno: bez env varijable test se PRESKAČE, vidi baseline ispod), a
daje trajnu regresionu zaštitu za budući `DENT-IMPROVE-013+` rad koji će
stvarno raditi nad Postgres.

### 5. Rollback plan

Sve izmjene su aditivne i granaju se isključivo na prisustvo
`DATABASE_URL` env varijable:

1. Uklanjanjem/nepostavljanjem `DATABASE_URL`, `backend/main.py`
   (`get_session_factory`) i `migrations/env.py` se ponašaju **identično**
   kao prije taska — SQLite preko `DENTALAND_DB_PATH`, potvrđeno testom
   (374 passed, isti broj kao prije-task baseline).
2. SQLite fajl (`dentaland.db`, bilo koji) se **nikad ne briše ni
   premješta** u ovom tasku ili ovom skriptu — migracioni skript samo čita
   (`mode=ro`, potvrđeno testom da piše baca grešku) iz izvora i piše u
   Postgres; izvor ostaje netaknut u svakom scenariju.
3. Ako Postgres grana treba potpuno ukloniti: grana `task/DENT-IMPROVE-012-postgres-migration`
   se još nije mergovala u `main` — dovoljno je ne mergovati je (ili
   revert prije merge-a nije ni potreban, samo se odbaci PR/merge).
4. Nema nepovratne izmjene na produkcijskim/stvarnim podacima — jedina
   baza koja je stvarno primila podatke u ovom tasku je izolovana lokalna
   `dentaland_test` (port 5433), koja se po potrebi može u potpunosti
   obrisati/ponovo kreirati (`DROP DATABASE dentaland_test` pa
   `alembic upgrade head` ponovo) bez ikakvog uticaja na `dentaland_dev`
   ili SQLite podatke.

### 6. Ruff/mypy/pytest baseline (bez `DATABASE_URL`)

Izmjereno u ovoj sesiji, upoređeno sa baseline iz `.agent/CURRENT_STATE.md`
(26.8.2026, 374 passed):

- `pytest tests/ -q` (bez `DATABASE_URL`/`DATABASE_URL_TEST`) →
  **374 passed, 1 skipped**, 11 warnings, ~17.5s. Skip je novi
  `test_postgres_migration.py` test (očekivano i namjerno — vidi gore).
  Broj `passed` **identičan** baseline-u prije taska — default SQLite put
  nije pokvaren.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py
  scripts/migrate_sqlite_to_postgres.py` → **All checks passed** (uključen
  i novi skript).
- `mypy src/dentaland backend` → **Success: no issues found in 52 source
  files** — isti broj fajlova kao baseline (52).
- `scripts/migrate_sqlite_to_postgres.py` NIJE pokriven mypy baseline
  komandom (koja cilja samo `src/dentaland`/`backend`) — provjereno da ni
  postojeći `scripts/dev_local.py`/`scripts/coordination.py` ne prolaze
  samostalan `mypy` (isti `TextIO`/missing-annotation obrazac), pa ovo
  nije regresija specifična za ovaj task nego postojeća konvencija da
  `scripts/` nije pod mypy ugovorom.

### 7. Postgres driver — izabran `psycopg2-binary`

Odluka prethodne sesije, potvrđujem i prenosim: `psycopg2-binary>=2.9`
(već instaliran, v2.9.12) umjesto `psycopg[binary]` (psycopg3), jer plain
`postgresql://` URL format u `.env` (`DATABASE_URL`/`DATABASE_URL_TEST`)
odgovara psycopg2 SQLAlchemy default dijalektu bez prefiksa — psycopg3 bi
zahtijevao `postgresql+psycopg://` i izmjenu `.env` formata, što nije u
dozvoljenim putanjama i nepotrebno usložnjava reprodukciju za reviewera.

## Acceptance criteria — status

- [x] `DATABASE_URL` postavljen → backend konektuje se na Postgres, CRUD
      radi (smoke: booking-request submit/confirm/409-conflict kroz
      `test_postgres_migration.py`, sve preko postojećeg `backend/main.py`
      API-ja)
- [x] `DATABASE_URL` NIJE postavljen → ponašanje identično prije taska
      (374 passed, isti broj)
- [x] `alembic upgrade head` radi čisto na praznoj/postojećoj Postgres
      bazi
- [x] migracioni skript postoji, testiran na sintetskim podacima, sa
      integrity izvještajem
- [x] overlap zaštita (409) potvrđena nad Postgres konekcijom
- [x] nijedna EXCLUDE/gist referenca nije dodana (potvrđeno i preko
      `pg_constraint` upita — samo CHECK constraint postoji)
- [x] ruff/mypy/postojeći pytest ostaju čisti
- [x] `.env` sa stvarnim kredencijalima nije commitovan (`git status`
      ispod)

## `git status --short` (finalna provjera prije predaje)

```text
## task/DENT-IMPROVE-012-postgres-migration
 M backend/main.py
 M docs/DENTALAND_IMPROVEMENT_BACKLOG.md
 M migrations/env.py
 M pyproject.toml
?? agent_reports/2026-08-27-DENT-IMPROVE-012-plan.md
?? agent_reports/2026-08-27-DENT-IMPROVE-012-postgres-migration.md
?? agent_reports/DENT-IMPROVE-012-task-contract.md
?? scripts/migrate_sqlite_to_postgres.py
?? tests/test_postgres_migration.py
```

`.env` nije u listi (gitignored, potvrđeno i ranije u sesiji). Nema
tracked ni untracked promjena van `allowed_paths` iz Task Contracta.

## Odbačene opcije (ova sesija, dopuna plana)

- **`scripts/seed_synthetic_sqlite.py` kao tracked fajl** — razmotreno,
  odbačeno u korist privremenog skripta van git trackinga (scratchpad).
  Task Contract `allowed_paths` eksplicitno navodi samo
  `scripts/migrate_sqlite_to_postgres.py` kao novi fajl pod `scripts/`;
  dodavanje drugog novog tracked fajla van te liste bi bio sitan scope
  creep bez jasne koristi (seed skript je jednokratan alat za generisanje
  test fixture-a, ne dio trajne migracione infrastrukture koju bi neko
  drugi trebao ponovo pokretati). Sintetska baza i skript koji je generiše
  ostaju van worktree-a (scratchpad), reproducibilnost je dokumentovana u
  ovom izvještaju (tačan sadržaj: 3 doktora, 3 usluge, 15 working_hours, 2
  time_off, 6 appointments — po jedan za svaki status).
- **Parametrizacija `tests/test_backend.py` preko fixture-a za oba
  dijalekta** — odbačeno (već navedeno u planu), potvrđujem istu odluku:
  fokusiran novi test manji je i bezbjedniji diff.
- **Truncate `dentaland_test` nakon evidence-run-a** — odbačeno; podaci su
  ostavljeni namjerno kao inspektabilan artefakt za reviewera (svi
  sintetski, izolovana test baza).

## Za reviewera (Codex obavezan, Pi/Crush kao Reviewer 2)

Molim posebno provjeriti:
1. Da OUT_OF_SCOPE_FINDING o `dentaland.db` gore stvarno stigne do
   Radovana (nije sahranjen) — ovo je ključna napomena ovog izvještaja.
2. Da `scripts/migrate_sqlite_to_postgres.py` zaista radi FK-safe
   redoslijed i da integrity provjera nije površna (traženo u Task
   Contractu kao presedan iz REF-02/REF-05) — vidi FK spot-check i status
   spot-check implementaciju, ne samo row count.
3. Da `tests/test_postgres_migration.py` ispravno SKIPUJE bez
   `DATABASE_URL_TEST` (ne pukne) — reprodukovano lokalno, ali vrijedi
   nezavisno potvrditi u čistom okruženju.
4. Da nijedan `EXCLUDE`/`btree_gist` trag nije ušao nigdje (scope creep na
   pravno blokiran dio) — potvrđeno lokalno preko `pg_constraint`, ali
   grep cijelog diff-a je jeftina dodatna provjera.
