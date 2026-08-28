---
task_id: DENT-IMPROVE-012
risk: HIGH
implementer: claude
reviewers: [codex, pi]
status: "DONE — MERGED u main (merge commit 824590f, 27.8.2026). SQLite→PostgreSQL migracija bez EXCLUDE constrainta (odvojeno u budući task zbog nerješenog pravnog pitanja). Dva fix kruga (Codex F1: percent-encoded DATABASE_URL; Pi nalaz potvrđen Crush-em: bezuslovan override pregazio test-izolovanu SQLite bazu). Review: Codex+Pi+Crush (svi PASS_WITH_NOTES). Radovan human approval 27.8.2026. Otvara DENT-IMPROVE-013."
created_at: 2026-08-26
---

# DENT-IMPROVE-012 — SQLite→PostgreSQL migracija (BEZ EXCLUDE constraint-a)

## Kontekst

`docs/DENTALAND_IMPROVEMENT_BACKLOG.md` sekcija 13 — originalno HIGH,
tip architecture/migration, jedini trenutno neblokiran Prioritet C task
(`DENT-IMPROVE-013/014/015` eksplicitno čekaju ovaj).

**VAŽNO ODSTUPANJE od originalnog backlog opisa** (Radovanova odluka
26.8.2026, zapisano u `.agent/CURRENT_STATE.md`): originalni backlog traži
`btree_gist` + `EXCLUDE USING gist` u ISTOM tasku. To je namjerno
razdvojeno zbog pravnog blokera — `CLAUDE.md` sekcija "Otvorena pitanja"
(pravni osnov obrade, rokovi čuvanja medicinske dokumentacije,
kontrolor/obrađivač ugovor, hosting lokacija) je **potvrđeno i dalje
otvorena**. Ovaj task radi SAMO migraciju konekcije/podataka na
PostgreSQL i zadržava postojeću aplikacionu overlap zaštitu
(`validate_appointment_overlap`, REF-01/DENT-IMPROVE-010) **nepromijenjenu**.
EXCLUDE constraint ide u poseban, budući, eksplicitno blokiran task — **ne
otvarati ga ovdje** čak i ako izgleda lako dodati usput.

**Pristup bazi riješen 26.8.2026:** kreirana potpuno izolovana lokalna
PostgreSQL 16 instanca SAMO za Dentaland — zaseban proces, port **5433**,
data-dir `C:\Users\38765\AppData\Local\Dentaland\pgdata16`. Ovo NIJE isti
servis kao Windows `postgresql-16` servis na portu 5432 koji koristi
`deklarant_pro` (drugi projekat, drugi podaci) — **implementer nikad ne
smije ni slučajno ciljati port 5432**. Kredencijali (`DATABASE_URL`,
`DATABASE_URL_TEST`) i start/stop komande su u `.env` u root-u repoa
(gitignored, ne u repou). Instanca se ne pokreće automatski pri restartu
računara — provjeriti da je running (`pg_ctl status` ili pokušaj konekcije)
prije početka rada.

## Trenutno stanje repoa (provjereno 26.8.2026, prije pisanja kontrakta)

- `backend/main.py:47` (`_build_session_factory`) hardkodirano
  `create_engine(f"sqlite:///{db_path}")`, `db_path` iz `DENTALAND_DB_PATH`
  env var (default `"dentaland.db"`). Nema `DATABASE_URL` grane.
- `pyproject.toml` dependencies **nemaju** Postgres driver (ni `psycopg2`
  ni `psycopg`) — mora se dodati.
- `alembic.ini:4` — `sqlalchemy.url = sqlite:///dentaland.db` hardkodirano;
  `migrations/env.py` trenutno čita samo iz `alembic.ini` (`fileConfig`),
  nema env var override.
- `src/dentaland/models.py:54` (`TZDateTime`) je već portabilan generički
  `DateTime` tip — potvrđeno da ne zahtijeva izmjenu za Postgres.
- 3 od 5 migracija (`migrations/versions/b2c3d4e5f6a7_*`, `c3d4e5f6a7b8_*`,
  `d4e5f6a7b8c9_*`) koriste `op.batch_alter_table(..., recreate="always")`
  — SQLite-specifičan obrazac za ALTER TABLE emulaciju. Na PRAZNOJ Postgres
  bazi bezopasan (nema šta da rekreira), ali implementer MORA izmjeriti
  (ne pretpostaviti) da `alembic upgrade head` ispravno gradi finalnu
  šemu na svježoj Postgres instanci.
- `desktop/`, `src/dentaland/backup.py`, `backup_cli.py` ostaju
  SQLite-specifični za Fazu 0 (desktop) — **van obima** ovog taska;
  Postgres backup (`pg_dump`) je poseban budući task.
- Ne postoji test/conftest infrastruktura koja već cilja Postgres —
  implementer je prvi koji uvodi taj put.

## Cilj

Omogućiti da `backend/main.py` FastAPI sloj radi nad PostgreSQL bazom
umjesto SQLite, uz `DATABASE_URL` konfigurabilnost, potvrđenu Alembic
migraciju na svježoj Postgres instanci, i dokazan (dry-run, sintetski
podaci) put kopiranja postojećih SQLite podataka u Postgres sa provjerom
integriteta — sve bez uvođenja EXCLUDE constraint-a ili bilo kakve izmjene
šeme koja pretpostavlja njegovo buduće postojanje.

## Required scope (iz CURRENT_STATE.md dogovora, NE iz originalnog backlog opisa)

1. `DATABASE_URL` env var podrška u `backend/main.py` — kad je postavljen,
   koristi se (Postgres); kad nije, zadržati postojeće SQLite ponašanje
   (`DENTALAND_DB_PATH`) nepromijenjeno kao default (desktop Faza 0 i
   postojeći testovi ne smiju se pokvariti).
2. Dodati Postgres driver zavisnost u `pyproject.toml` (implementer bira
   `psycopg[binary]` v3 ili `psycopg2-binary` — dokumentovati izbor i
   razlog u izvještaju).
3. `migrations/env.py`: dodati `DATABASE_URL` override (standardni Alembic
   obrazac — env var ima prednost nad `alembic.ini` vrijednošću) — ne
   brisati postojeći sqlite default u `alembic.ini` (desktop i dalje mora
   raditi bez env varijable).
4. Dokazati (izvještaj + evidencija) da `alembic upgrade head` na PRAZNOJ
   `dentaland_test` Postgres bazi (kredencijali u `.env`) uspješno gradi
   finalnu šemu identičnu SQLite šemi (uporediti kolone/tipove/enum
   vrijednosti).
5. Napisati jednokratan migracioni skript (npr.
   `scripts/migrate_sqlite_to_postgres.py`) koji kopira podatke iz
   postojeće SQLite baze u Postgres — SAMO nad SINTETSKIM/test podacima
   (vidi Critical constraints), FK-safe redoslijed insertovanja, očuvane
   `TZDateTime` vrijednosti (UTC-aware).
6. Integrity checks nakon kopiranja: row count po tabeli (SQLite vs
   Postgres), spot-check FK referenci, spot-check enum/status vrijednosti.
7. Potvrditi da postojeća aplikaciona overlap zaštita
   (`validate_appointment_overlap`, `src/dentaland/services/availability.py`)
   i dalje ispravno radi i baca `OverlapError` → `409` kad backend radi nad
   Postgres (isti test scenario kao postojeći `tests/test_backend.py`,
   samo pokrenut i nad Postgres konekcijom) — **ne mijenjati tu logiku**,
   samo dokazati da radi nepromijenjena na novom dijalektu.
8. Rollback plan — dokumentovan povratak na SQLite (ukloniti/promijeniti
   `DATABASE_URL`) bez gubitka podataka, jer se SQLite fajl ne
   dira/briše u procesu (kopiranje, ne premještanje).

## Critical constraints (CLAUDE.md + backlog + Radovanova odluka)

- **Nikad ne migrirati direktno na produkcijskim/stvarnim pacijentskim
  podacima u ovom tasku.** Ako implementer otkrije da lokalni dev SQLite
  fajl (`dentaland.db`) sadrži stvarne pacijentske podatke (ne
  sintetske/test), **STATI** i prijaviti kao `OUT_OF_SCOPE_FINDING`/
  eskalirati Radovanu prije bilo kakvog kopiranja — ne pretpostaviti da su
  podaci sintetski.
- DB constraint kao "finalni autoritet za overlap" (iz originalnog
  backlog opisa) **nije cilj ovog taska** — to eksplicitno čeka budući
  EXCLUDE constraint task. Ne dodavati nikakav privremeni/djelimičan
  DB-level overlap mehanizam kao zamjenu.
- Manual override ponašanje (postojeće) se ne dira.
- Nikad ne koristiti Windows `postgresql-16` servis na portu 5432
  (`deklarant_pro`) — samo izolovanu instancu na portu 5433 iz `.env`.
- Ne mijenjati `desktop/**` (Faza 0 ostaje SQLite, ovaj task ne dira
  desktop sloj).
- Ne dodavati `EXCLUDE`/`btree_gist` bilo gdje u `models.py` ili
  migracijama.

## Required evidence (iz backloga, obavezno u izvještaju)

- [ ] migration dry-run izlaz (log/output `alembic upgrade head` na
      praznoj `dentaland_test`)
- [ ] row count comparison tabela (SQLite izvor vs Postgres odredište, po
      tabeli)
- [ ] conflict test rezultat (overlap → 409 potvrđen nad Postgres
      konekcijom)
- [ ] rollback plan (pisano, korak-po-korak)
- [ ] dva nezavisna reviewera (Codex Reviewer 1 obavezan, Pi ili Crush
      Reviewer 2)
- [ ] human approval (Radovan) prije merge-a

## Acceptance criteria

- [ ] `DATABASE_URL` postavljen → `backend/main.py` konektuje se na
      Postgres, CRUD radi (bar smoke: create/list/confirm/reject request
      preko postojećih testova ili ekvivalentnog ručnog scenarija)
- [ ] `DATABASE_URL` NIJE postavljen → ponašanje identično prije taska
      (SQLite, `DENTALAND_DB_PATH`) — postojeći `pytest tests/ -q` prolazi
      bez izmjene default putanje
- [ ] `alembic upgrade head` radi čisto na praznoj Postgres bazi
- [ ] migracioni skript za kopiranje SQLite→Postgres postoji, testiran na
      sintetskim podacima, sa integrity izvještajem
- [ ] overlap zaštita (409 na konflikt) potvrđena nad Postgres konekcijom
- [ ] nijedna EXCLUDE/gist referenca nije dodana
- [ ] `ruff`/`mypy`/postojeći `pytest` ostaju čisti
- [ ] `.env` sa stvarnim kredencijalima NIJE commitovan (provjeriti
      `git status` prije commit-a)

## Allowed paths

```text
backend/main.py
pyproject.toml
alembic.ini                              (samo ako je nužno, dokumentovati zašto — env.py override je preferovan pristup)
migrations/env.py
scripts/migrate_sqlite_to_postgres.py    (novo)
tests/test_backend.py                    (samo ako treba parametrizovati DB dijalekt za novi test slučaj, ne mijenjati postojeće scenarije)
tests/test_postgres_migration.py         (novo, opciono — automatizovan test umjesto samo ručne evidencije)
agent_reports/**
docs/DENTALAND_IMPROVEMENT_BACKLOG.md    (samo status napomena na kraju, ne mijenjati opis obima)
```

## Forbidden paths

```text
desktop/**
src/dentaland/models.py                  (READ-ONLY referenca — TZDateTime već portabilan, ne dirati šemu)
src/dentaland/services/availability.py   (READ-ONLY referenca — overlap logika se ne mijenja)
src/dentaland/backup.py
src/dentaland/backup_cli.py
migrations/versions/**                   (postojeće migracije se NE prepravljaju; nova migracija dozvoljena SAMO uz prethodno prijavljen OUT_OF_SCOPE_FINDING zašto je neophodna)
web/**
```

## Review

Standardan HIGH proces: Codex (Reviewer 1, obavezan) + Pi ili Crush
(Reviewer 2, po dostupnosti), Radovanov human approval prije merge-a.
Implementer je Claude (`CLAUDE.md`: "šema/migracije i dalje isključivo
HIGH kroz Claude") u svom worktree-u; review u nezavisnoj sesiji/kontekstu
(ne ista sesija koja je pisala kod).

Reviewer posebno provjerava:

- da nijedan EXCLUDE/`btree_gist` trag nije ušao u ovaj task (scope creep
  na pravno blokiran dio);
- da SQLite/desktop Faza 0 ponašanje nije pokvareno (default bez
  `DATABASE_URL`);
- da migracioni skript stvarno radi FK-safe redoslijed i da integrity
  provjera nije površna (isti presedan kao REF-02/REF-05: ne prihvatiti
  test koji provjerava samo "nije pukao", nego stvarno poređenje redova);
- da `.env`/kredencijali nisu procurili u diff ili commit.

## Koordinacija

Nema paralelnih zadataka trenutno aktivnih na ovim putanjama.

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-012 --agent claude --paths backend/main.py,pyproject.toml,migrations/env.py
```

prije početka rada, po standardnoj proceduri iz
`docs/dentaland-agentski-razvoj.md`.

## Plan prije izmjene (HIGH — obavezno prije editovanja)

Implementer piše kratak plan (Cilj / Pogođeno / Plan / Šta NE dirati /
Plan verifikacije / Rollback / Odbačene opcije) u `agent_reports/` PRIJE
prve izmjene koda (`docs/dentaland-agentski-razvoj.md`, "Obavezna
procedura prije izmjene", korak 5) — ovaj Task Contract nije zamjena za
taj korak.
