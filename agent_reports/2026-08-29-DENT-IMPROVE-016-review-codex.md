---
task_id: DENT-IMPROVE-016
reviewer: codex
review_type: independent_security_privacy_release_gate_review
verdict: REJECT
scope: PASS
acceptance: FAIL
blocking_findings:
  - F1: "Restore verifikacija ne dokazuje integritet niti identičnost podataka"
  - F2: "Deterministički naziv i bezuslovni DROP mogu obrisati postojeću ne-privremenu bazu"
  - F3: "Kvar neposredno nakon CREATE DATABASE ostavlja privremenu bazu iza sebe"
  - F4: "DATABASE_URL sa lozinkom se prosljeđuje kroz command-line argumente pg_dump/pg_restore procesa"
reviewed_commit: 9b20d22db9415b469718177fbe284e4109ba2147
reviewed_at: 2026-08-29
---

# DENT-IMPROVE-016 — Codex review

## CILJ

Nezavisno provjeriti skraćeni HIGH-risk security/privacy release gate:
PostgreSQL backup/restore sigurnost i integritet, cleanup/destruktivne
granice, compliance dokumente, pravne rokove i scope.

## URAĐENO

Verdikt je **REJECT**. Scope i dokumentacioni dio su uredni, ali backup
jezgro ima četiri blokirajuća nalaza.

## BLOCKING FINDINGS

### F1 — HIGH: Restore verifikacija ne dokazuje integritet niti identičnost podataka

**Evidence:** `src/dentaland/backup_postgres.py:221-234` izvršava samo
`SELECT COUNT(*) FROM appointments`, pozove `fetchone()` i odbaci rezultat.
`tests/test_backup_postgres.py:87-116` seeduje `Doctor` red, ali nikad ne
otvara restoreovanu bazu niti potvrđuje da taj red postoji u njoj. Drugi test
provjerava samo da je isti red ostao u izvornoj bazi.

**Adversarna reprodukcija:** kreirana je nasumično imenovana privremena baza
koja sadrži samo praznu tabelu `appointments(id integer)`, bez Dentaland
šeme i bez podataka. `_verify_postgres_db` ju je prihvatio:
`EMPTY_APPOINTMENTS_ONLY_DB_ACCEPTED_BY_VERIFIER=True`.

**Failure path:** prazan/nepotpun dump koji ipak kreira praznu
`appointments` tabelu prolazi kao “verifikovan”. Čak ni broj redova nije
provjeren, a seedovani `Doctor` marker nikad nije pročitan iz restoreovane
baze.

**Impact:** acceptance kriterij “podaci čitljivi i identični” nije
zadovoljen; operativna poruka može lažno tvrditi da je backup upotrebljiv.

**Minimal correction:** tokom stvarnog restore testa provjeriti poznate
seedovane vrijednosti u privremenoj bazi (test mora dokazati da marker
`Doctor` iz dumpa postoji) i u produkcijskoj verifikaciji koristiti
smislen manifest/broj redova za relevantne tabele ili precizno suziti
tvrdnju ako se provjerava samo čitljivost šeme. Dodati mutacioni test koji
bi pao kada restore vrati praznu/nepotpunu bazu.

### F2 — HIGH: Deterministički naziv može obrisati postojeću bazu

**Evidence:** `src/dentaland/backup_postgres.py:47,188-206` gradi uvijek
isto ime `<izvorna_baza>_restore_check`, zatim prije kreiranja bezuslovno
izvršava `DROP DATABASE IF EXISTS <to_ime>`.

**Failure path:** ako administrator, drugi test/job ili stvarna aplikacija
već koristi bazu sa tim imenom, `restore-test` je smatra svojim ostatkom i
pokušava je obrisati. Nema ownership markera, nasumičnog identifikatora ni
provjere da ju je ovaj proces kreirao.

**Impact:** mogući nepovratan gubitak druge PostgreSQL baze; tvrdnja
“nikad ne može dodirnuti aktivnu/ne-privremenu bazu” nije tačna.

**Minimal correction:** svaki run mora koristiti jedinstveno, strogo
prefiksirano ime sa sigurnim random/UUID sufiksom i smije brisati samo ime
koje je taj run generisao. Ne raditi pre-emptive `DROP` determinističkog
imena. Cleanup zastarjelih baza treba biti zasebna, eksplicitna operacija sa
ownership dokazom.

### F3 — MEDIUM: Post-create failure zaobilazi cleanup

**Evidence:** u `restore_test` (`src/dentaland/backup_postgres.py:278-286`)
poziv `_create_throwaway_database(...)` stoji prije unutrašnjeg
`try/finally` koji poziva `_drop_throwaway_database(...)`.

**Adversarna reprodukcija:** wrapper je pozvao stvarni
`_create_throwaway_database`, zatim namjerno podigao `RuntimeError` prije
povratka. Poslije `restore_test` izuzetka baza je i dalje postojala:
`DB_LEFT_BEHIND_AFTER_POST_CREATE_FAILURE=True`; reviewer ju je zatim ručno
obrisao. Odvojeno je potvrđeno da običan `_run_pg_restore` failure jeste
očišćen (`FORCED_RESTORE_FAILURE_CLEANUP=PASS`).

**Impact:** nije tačna tvrdnja da privremena baza uvijek biva obrisana na
svim failure putanjama; prekid/izuzetak na granici kreiranja ostavlja bazu.

**Minimal correction:** generisano ime i cleanup `finally` uspostaviti prije
pokušaja kreiranja; za jedinstveno ime ovog runa bezbjedno je pokušati
`DROP IF EXISTS` u spoljašnjem cleanup-u čak i ako create poziv nije uredno
vratio. Dodati trajni regresioni test za “create uspio, zatim izuzetak”.

### F4 — MEDIUM: DB lozinka završava u command-line argumentima

**Evidence:** `_run_pg_dump` na `src/dentaland/backup_postgres.py:166-174`
stavlja cijeli `database_url` u argv, a `_run_pg_restore` na linijama
176-185 stavlja `--dbname=<target_url>`; `_throwaway_url` eksplicitno koristi
`render_as_string(hide_password=False)`.

**Failure path:** ako `DATABASE_URL` sadrži lozinku, ona je tokom procesa
vidljiva u komandnoj liniji/procesnoj inspekciji i može završiti u
dijagnostičkim alatima. Enkripcija dumpa ne štiti taj kredencijal.

**Impact:** nepotrebno izlaganje produkcijskog DB kredencijala u tasku koji
predstavlja security release gate.

**Minimal correction:** parsirati URL i proslijediti host/port/user/db bez
lozinke kroz argv; autentifikaciju riješiti standardnim PostgreSQL
mehanizmom (`.pgpass`/passfile ili pažljivo ograničenim `PGPASSWORD` env
kanalom), bez ispisa tajne u greškama/testovima.

## POTVRĐENO ISPRAVNO

- Diff je u potpunosti unutar `allowed_paths`; `web/privacy.html`, SQLite
  backup, modeli, migracije, desktop i backend nisu dirani.
- Šest PostgreSQL backup testova stvarno prolaze nad izolovanim
  `DATABASE_URL_TEST`: **6 passed**.
- Običan `pg_restore` failure briše privremenu bazu i plain dump; problem F3
  je uža post-create granica.
- Aktivna test baza ostaje sa svojim marker redom nakon normalnog restore
  testa.
- Sva četiri nova dokumenta su na srpskom/bosanskom latinicom; pretraga
  ćiriličnih znakova dala je 0 pogodaka. Tehnički termini na engleskom ne
  mijenjaju jezik dokumenta.
- Retention dokument koristi potvrđenih **pet godina** i eksplicitno navodi
  da automatsko brisanje/anonimizacija nije implementirano. Ne propisuje
  rok medicinske dokumentacije koji je u `CLAUDE.md` izvan Dentaland
  sistema.
- Breach runbook koristi potvrđeni **72h** rok iz `CLAUDE.md`, isti kontakt
  Agencije kao `web/privacy.html`, te ne uvodi drugi numerički pravni rok.
- Audit `web/privacy.html` je opravdano ocijenjen kompletnim za ugovoreni
  scope i sam fajl nije mijenjan.

## VERIFIKACIJA

- `pytest tests/test_backup_postgres.py -v` sa `DATABASE_URL_TEST` →
  **6 passed**.
- `pytest tests/ -q` bez PostgreSQL env varijable → **429 passed, 8
  skipped**.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`
  → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 55
  source files**.
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.
- Puni suite sa `DATABASE_URL_TEST` → **435 passed, 2 failed**. Neuspjesi
  su nezavisno reprodukovani: stari Postgres 409 test dobija 401 jer nema
  novu RBAC prijavu, a lokalni `alembic_version` je `d4e5f6a7b8c9` umjesto
  head-a. DENT-IMPROVE-016 diff ne dira nijedan povezani fajl, pa su to potvrđeni
  pre-postojeći/out-of-scope problemi i nisu razlog ovog REJECT-a.

## NE DIRATI

- Ne popravljati RBAC Postgres test ili lokalni Alembic pečat u ovom tasku.
- Ne širiti task na HTTPS, hosting, processor ugovor ili `EXCLUDE`
  constraint.
- Ne mijenjati `web/privacy.html` bez Radovanovog odobrenja.

## SLJEDEĆE

Implementer treba popraviti F1-F4 i dodati adversarne regresione testove za
integritet, ownership naziva baze i post-create cleanup. Nakon toga Codex
ponavlja ciljanu verifikaciju; tek poslije PASS-a ide Reviewer 2 i Radovanov
human approval.
