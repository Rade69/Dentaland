---
task_id: DENT-IMPROVE-016
risk: HIGH
implementer: claude
reviewers: [codex]
status: "FIX RUNDA 2 GOTOVA — Codex REJECT dva puta (F1-F4, pa dublji F1/F2/F4). Sada: content-digest manifest (F1), ownership-based cleanup bez pre-emptive DROP (F2), password i iz query-stringa (F4). 7 adversarnih regresionih testova. Ceka Codex re-review, pa human approval. Vidi 2026-08-29-DENT-IMPROVE-016-release-gate.md."
created_at: 2026-08-29
depends_on: DENT-IMPROVE-012, DENT-IMPROVE-013, DENT-IMPROVE-014, DENT-IMPROVE-014B, DENT-IMPROVE-014C, DENT-IMPROVE-015
---

# DENT-IMPROVE-016 — Produkcijski security/privacy release gate (skraćen obim)

## Kontekst

Originalno `DENT-IMPROVE-015` u `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`
sekcija 16 (HIGH, Prioritet C6) — broj je greškom ponovo iskorišten
28.8.2026 za rate limiting task (sad ispravno pod tim brojem, ovaj task
preimenovan u 016, vidi backlog i `.agent/CURRENT_STATE.md` za istoriju
kolizije).

Pun release gate ima 13 stavki (vidi backlog sekciju 16 za kompletan
spisak). Radovan je 29.8.2026 eksplicitno odgodio izbor hosting/cloud
provajdera do kraja projekta (trenutno nema pristup/informaciju o
hostingu zvaničnog sajta ordinacije). Tri stavke direktno zavise od te
odluke i **NISU dio ovog taska**:

- HTTPS (fizički zahtijeva stvaran server),
- processor evidencija / kontrolor-obrađivač ugovor (zavisi od izabranog
  hosting providera),
- `EXCLUDE` constraint / PostgreSQL concurrency protection (namjerno
  izostavljeno iz `DENT-IMPROVE-012`, čeka istu odluku).

Ovo je dokumentovan, svjestan scope cut, ne blocking finding — pun gate
sa svih 13 stavki radi se tek kad hosting bude izabran (budući task,
nastavak na `DENT-IMPROVE-016`, isti ili nov ID po potrebi).

Dvije dodatne stavke su tokom pripreme ovog kontrakta provjerene i već
riješene, pa NISU dio required scope-a (samo se konstatuju):

- **Pravni osnov obrade** — riješeno kao poslovna odluka (Radovan,
  29.8.2026): obavještenje/pristanak na javnoj formi za zakazivanje.
- **Privacy notice** — VEĆ POSTOJI: `web/privacy.html`, napisao Radovan
  lično 17.8.2026 (commit `16d0a17`), sadržajno kompletan (kontrolor,
  svrha, pravni osnov, obavezni podaci, primaoci, retention, prava,
  Agencija za zaštitu ličnih podataka BiH, maloljetna lica,
  automatizovano odlučivanje). Ovaj task ga AUDITUJE (provjerava
  usklađenost sa CLAUDE.md/v3.1 zahtjevima), NE piše ispočetka.

**Retention period ispravka (bitno za implementera):** tokom pripreme
ovog kontrakta otkrivena je i ispravljena greška — CLAUDE.md je ranije
netačno navodio "12 mjeseci automatska anonimizacija", dok
`web/privacy.html` (već u produkciji od 17.8.2026) kaže **pet godina** od
posljednjeg unosa za booking podatke. Radovan je 29.8.2026 potvrdio da je
tačno pet godina — CLAUDE.md je ispravljen (commit `0c83433`). Implementer
MORA koristiti pet godina, ne 12 mjeseci, u retention dokumentu.
**Nikakav kod trenutno ne implementira ni jednu ni drugu vrijednost** —
`grep` za `anonymiz`/`retention` u `src/` ne vraća ništa — ovo je čisto
dokumentacioni task, automatska anonimizacija/brisanje nije
implementirana i NIJE dio ovog taska (spomeni kao `open_risks` u gate
outputu).

## Cilj

Proizvesti djelimičan release-gate verdikt (format iz backloga:
`verdict`/`blocking_findings`/`evidence`/`open_risks`) za 5 stavki koje
NE zavise od hosting odluke, plus napraviti/dopuniti stvarne artefakte
koji trenutno fale.

## Required scope

1. **PostgreSQL backup + testiran restore** (CLAUDE.md zahtjev: "Dnevni
   `pg_dump` backup (Faza 1+) + **testiran** restore, ne samo napravljen").
   - Nov modul (npr. `src/dentaland/backup_postgres.py`), CLI sloj po
     uzoru na postojeći `src/dentaland/backup_cli.py` (tri komande: `run`,
     `restore-test`, `status`; non-zero exit kod na grešku).
   - Koristi `pg_dump`/`pg_restore` (subprocess) ili logički dump preko
     `psycopg`/SQLAlchemy — implementer bira, dokumentuje zašto.
   - Enkripcija dumpa na disku — dosljedno sa postojećim SQLite backup
     pristupom (Fernet, ključ odvojeno od backup foldera). Ako implementer
     odluči da ne enkriptuje, mora eksplicitno obrazložiti zašto (booking
     podaci — ime/telefon/email — su u dumpu).
   - Radi protiv postojeće LOKALNE Dentaland Postgres instance (port
     5433, kredencijali iz `.env`) — ne čeka produkcijski VPS.
   - Test: `tests/test_backup_postgres.py` — backup pa restore u
     odvojenu/privremenu bazu ili šemu, provjera da su podaci čitljivi i
     identični (ne samo da fajl postoji).
   - Dokument: `docs/dentaland-postgres-backup-operativni-vodic.md`
     (po uzoru na `docs/dentaland-backup-operativni-vodic.md`).

2. **Breach runbook** — `docs/dentaland-breach-runbook.md`. Koraci:
   detekcija, containment, procjena (da li je ovo povreda ličnih
   podataka po zakonu), **72h rok prijave Agenciji za zaštitu ličnih
   podataka BiH** (obavezno za sve, bez obzira na veličinu — CLAUDE.md),
   kontakt podaci Agencije (već u `web/privacy.html` sekcija 9 — koristi
   iste), obavještavanje pogođenih pacijenata kad je rizik visok, interna
   evidencija incidenta, post-incident pregled. Srpski/bosanski latinica.

3. **Retention dokument** — `docs/dentaland-retention-politika.md`.
   Formalizuje: booking podaci (ime/email/telefon/datum/usluga) — pet
   godina od posljednjeg unosa (usklađeno sa `web/privacy.html`);
   medicinska dokumentacija ostaje isključivo u papirnoj formi kod
   ordinacije, van sistema, taj rok NIJE Dentalandova odgovornost.
   Eksplicitno navesti da automatska anonimizacija/brisanje NIJE
   implementirana u kodu (open risk, budući task).

4. **Politika "produkcijski podaci van AI/dev dumpova"** —
   `docs/dentaland-politika-produkcijski-podaci.md`. Pravilo: stvarni
   podaci pacijenata se nikad ne kopiraju u dev/test baze, lokalne
   dumpove, niti pokazuju AI agentima/upisuju u `agent_reports/`.
   Referencirati stvaran presedan: tokom `DENT-IMPROVE-012` (27.8.2026)
   implementer je pronašao 14 stvarnih pacijentskih zapisa u lokalnoj dev
   SQLite bazi, ispravno ih nije koristio, Radovan ih je naknadno obrisao
   i pokrenuo `VACUUM` — ovaj task formalizuje pravilo koje je tad
   neformalno primijenjeno.

5. **Audit `web/privacy.html`** (ne pisanje, provjera) — kratak nalaz
   (par rečenica u evidence izvještaju) da li dokument pokriva sve što
   CLAUDE.md/v3.1 zahtijevaju (kontrolor, svrha, pravni osnov, minimalni
   podaci, retention, prava, Agencija, maloljetni). Ako implementer nađe
   stvaran nedostatak, PRIJAVITI Radovanu (`OUT_OF_SCOPE_FINDING` ili
   direktno u izvještaju) — NE mijenjati dokument bez odobrenja, Radovan
   ga je lično napisao.

## Required output

Na kraju, u evidence izvještaju, popuniti (format iz backloga):

```yaml
verdict: PASS_WITH_NOTES   # pun PASS nije moguć - 3 stavke namjerno van scope-a
blocking_findings: []       # popuniti ako se nešto stvarno pokvari tokom rada
evidence: [...]              # linkovi na nove fajlove/testove/dokumente
open_risks:
  - "HTTPS, processor evidencija, EXCLUDE constraint namjerno odgođeni do hosting odluke"
  - "Automatska anonimizacija/brisanje nakon 5 godina nije implementirana u kodu"
  - "token sigurnost i minimalna javna forma nisu formalno auditovani ovim gate-om (vjerovatno OK, nije provjereno)"
```

## Šta NE dirati

- `web/privacy.html` — samo čitanje/audit, ne mijenjati sadržaj bez
  eksplicitnog Radovanovog odobrenja.
- `src/dentaland/backup.py`, `src/dentaland/backup_cli.py` (postojeći
  SQLite backup — ostaje netaknut, ovo je NOV, paralelan modul za
  Postgres, ne zamjena).
- `models.py`, `migrations/**` — ovo je operativni/dokumentacioni task,
  ne schema izmjena.
- Ne dirati HTTPS/deployment, ne birati hosting provajdera, ne pisati
  processor ugovor, ne raditi na `EXCLUDE` constraint — sve to je
  eksplicitno van obima.

## Acceptance criteria

- [ ] `src/dentaland/backup_postgres.py` + CLI (`run`/`restore-test`/`status`)
      rade protiv lokalne Dentaland Postgres instance
- [ ] `tests/test_backup_postgres.py` — backup pa restore, provjerena
      integritet podataka, ne samo postojanje fajla
- [ ] `docs/dentaland-postgres-backup-operativni-vodic.md` napisan
- [ ] `docs/dentaland-breach-runbook.md` napisan, uklj. 72h rok i kontakt
      Agencije
- [ ] `docs/dentaland-retention-politika.md` napisan, sa tačnim
      petogodišnjim rokom (NE 12 mjeseci)
- [ ] `docs/dentaland-politika-produkcijski-podaci.md` napisan, sa
      referencom na stvaran DENT-IMPROVE-012 presedan
- [ ] Kratak audit nalaz o `web/privacy.html` u evidence izvještaju
- [ ] `pytest tests/ -q`, `ruff`, `mypy`, `agent_sensors.py --all` ostaju
      čisti
- [ ] Evidence izvještaj sadrži popunjen `verdict`/`blocking_findings`/
      `evidence`/`open_risks` blok

## Allowed paths

```text
src/dentaland/backup_postgres.py   (nov fajl)
tests/test_backup_postgres.py      (nov fajl)
docs/dentaland-postgres-backup-operativni-vodic.md   (nov)
docs/dentaland-breach-runbook.md                     (nov)
docs/dentaland-retention-politika.md                 (nov)
docs/dentaland-politika-produkcijski-podaci.md        (nov)
agent_reports/**
```

## Forbidden paths

```text
web/privacy.html                   (samo čitanje)
src/dentaland/backup.py
src/dentaland/backup_cli.py
models.py
migrations/**
desktop/**
backend/**                          (osim ako implementer utvrdi da je stvarno potrebno - prijaviti prije nego što se dirne)
```

## Review

Codex (jedini reviewer — pravilo od 29.8.2026, vidi
`docs/dentaland-agentski-razvoj.md` "Uloge"; implementer je Claude, pa
Claude ne može biti reviewer istog zadatka). Human approval prije
merge-a. Codex posebno provjerava: (a) da li restore test stvarno verifikuje
integritet podataka a ne samo "fajl postoji", (b) da li su svi novi
dokumenti na srpskom/bosanskom latinicom, (c) da retention/breach
dokumenti ne izmišljaju pravne rokove van onoga što je već potvrđeno
(pet godina — `web/privacy.html`, 72h — CLAUDE.md).

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-016 --agent claude --paths src/dentaland/backup_postgres.py,tests/test_backup_postgres.py,docs/dentaland-postgres-backup-operativni-vodic.md,docs/dentaland-breach-runbook.md,docs/dentaland-retention-politika.md,docs/dentaland-politika-produkcijski-podaci.md
```

Nema poznatih zavisnosti/preklapanja sa drugim aktivnim taskovima —
Prioritet C je inače završen (vidi `.agent/CURRENT_STATE.md`).
