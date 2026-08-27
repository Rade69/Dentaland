# Dentaland — prijedlozi za unapređenje i agent-ready backlog

**Datum:** 2026-08-20  
**Repo:** `Rade69/Dentaland`  
**Namjena:** operativni backlog zadataka koji se mogu direktno dodjeljivati Claude Code, Codex, Pi, Crush ili drugim agentima  
**Polazno stanje (originalno):** desktop scheduler je funkcionalno najzreliji dio; agent-ready `.agent/` sloj je uveden; posljednji zabilježeni post-merge gate na `main` prijavljuje 219 prolazećih testova, čist `ruff` i čist `mypy`.

**Napomena (20.8.2026):** dokument je pisan prije `DENT-020` merge-a — trenutni `main` je na 222 prolazeća testa. `DENT-IMPROVE-008` je otad završen (vidi sekciju 9). Ostatak provjeren protiv trenutnog `main`-a istog dana i potvrđen validnim (8 od 9 A/B stavki).

---

# 0. Kako koristiti ovaj dokument

Ovaj dokument ne zamjenjuje postojeće:

- `CLAUDE.md`
- `AGENTS.md`
- `docs/dentaland-agentski-razvoj.md`
- `docs/dentaland-razvojni-plan-v3.1.md`
- postojeće Task Contracte u `agent_reports/`

On je **prioritizovan backlog unapređenja** nastao nakon pregleda trenutnog stanja repozitorijuma.

Za svaki task važe postojeća Dentaland pravila:

1. Task Contract prije izmjene.
2. Zaseban git worktree za netrivijalan write task.
3. LOW/MEDIUM/HIGH risk procedura.
4. Implementer != Reviewer.
5. Execution evidence prije review-a.
6. Review prije human approval-a.
7. Bez samovoljnog širenja scope-a.
8. `OUT_OF_SCOPE_FINDING` za relevantne nalaze van zadatka.

---

# 1. Prioriteti

## PRIORITET A — uraditi sada

1. `DENT-IMPROVE-001` — očistiti Context Debt u `.agent/`
2. `DENT-IMPROVE-002` — dodati GitHub Actions CI
3. `DENT-IMPROVE-003` — centralizovati runtime/data/resource putanje
4. `DENT-IMPROVE-004` — implementirati „Blokiraj vrijeme“
5. `DENT-IMPROVE-005` — minimalne Postavke
6. `DENT-IMPROVE-006` — pravi ekran „Novi zahtjevi“

## PRIORITET B — prije stvarne svakodnevne upotrebe

7. `DENT-IMPROVE-007` — operativni automatski backup
8. ~~`DENT-IMPROVE-008` — operativni scheduler za email podsjetnike~~ — DONE (`DENT-020`, 20.8.2026)
9. `DENT-IMPROVE-009` — Windows packaging + clean-machine test

## PRIORITET C — prije javnog online bookinga

10. ~~`DENT-IMPROVE-010` — objediniti overlap logiku~~ — DONE (nuspojava REF-01, 25.8.2026: `validate_appointment_overlap` u `availability.py` je jedini overlap izvor, `requests.py`/`booking.py` samo re-eksportuju; potvrđeno 26.8.2026, nikad prije eksplicitno zatvoreno pod ovim ID-jem)
11. ~~`DENT-IMPROVE-011` — browser E2E testovi javne forme~~ — DONE, 26.8.2026 (merge `f9de00e`; Playwright, 6 scenarija, F1 REJECT→fix za sigurnost izolovane test baze — vidi task contract za detalje)
12. ~~`DENT-IMPROVE-012` — PostgreSQL migracija~~ — DONE, 27.8.2026 (merge `824590f`; obim sužen — SAMO SQLite→PostgreSQL konekcija/podaci, BEZ EXCLUDE/`btree_gist` zbog nerešenog pravnog pitanja, odvojeno u budući task — vidi `agent_reports/2026-08-27-DENT-IMPROVE-012-postgres-migration.md` za detalje)
13. `DENT-IMPROVE-013` — autentifikacija + RBAC — **sad jedini neblokiran Prioritet C task**
14. `DENT-IMPROVE-014` — audit log
15. `DENT-IMPROVE-015` — produkcijski security/privacy release gate

---

# 2. DENT-IMPROVE-001 — Očistiti Context Debt u `.agent/`

**Risk:** LOW  
**Tip:** docs / agent workflow maintenance  
**Prioritet:** A1

## Problem

`.agent/CURRENT_STATE.md` i `.agent/TASK_ROUTING.md` već sadrže zastarjele ili istorijske dijelove. Istorijski detalji troše tokene i razvodnjavaju aktivna pravila.

## Objective

Smanjiti always-read kontekst bez gubitka istorije.

## Read first

- `AGENTS.md`
- `CLAUDE.md`
- `.agent/CURRENT_STATE.md`
- `.agent/TASK_ROUTING.md`
- `.agent/PROJECT_MAP.md`
- `agent_reports/README.md`
- relevantne DENT-AGENT-CONTEXT izvještaje

## Allowed paths

```text
.agent/CURRENT_STATE.md
.agent/TASK_ROUTING.md
agent_reports/
```

## Forbidden paths

```text
src/
desktop/
backend/
web/
migrations/
tests/
```

## Required changes

### `CURRENT_STATE.md`

Ostaviti samo:

- trenutni aktivni fokus,
- trenutno raspoložive agente ako je relevantno,
- trenutni verification baseline,
- aktivna poznata ograničenja,
- sljedeći poznati prioritet.

Ukloniti istoriju završenih taskova ako već postoji u `agent_reports/`.

### `TASK_ROUTING.md`

Ostaviti samo aktivne routing pakete:

- Bug
- Feature
- Desktop GUI
- Booking/service
- Schema/migration
- Public web/API
- Review

Cijelu validacionu istoriju premjestiti u jedan postojeći ili novi agent report.

## Acceptance criteria

- `CURRENT_STATE.md` nema kontradiktorne aktivne statuse.
- `TASK_ROUTING.md` sadrži routing pravila, ne eksperimentalni dnevnik.
- Nijedno važno aktivno pravilo nije izgubljeno.
- Istorijska validacija ostaje sačuvana u `agent_reports/`.
- Svi linkovi iz `AGENTS.md`/`CLAUDE.md` ostaju validni.

## Verification

```bash
git diff --check
```

Ručno:

- fresh agent treba moći pročitati oba fajla bez nailaska na zastarjeli status,
- uporediti uklonjenu istoriju sa reportom u kojem je sačuvana.

## Done evidence

- diff summary,
- broj linija prije/poslije,
- lista premještenih istorijskih sekcija,
- reviewer potvrđuje da nije izgubljeno kanonsko pravilo.

---

# 3. DENT-IMPROVE-002 — Dodati GitHub Actions CI

**Risk:** LOW  
**Tip:** developer tooling / quality gate  
**Prioritet:** A2

## Problem

Lokalno postoje jasne komande za `pytest`, `ruff` i `mypy`, ali nema automatskog GitHub CI gate-a za push/PR.

## Objective

Automatski pokretati statičke provjere i test suite na GitHubu.

## Read first

- `README.md`
- `pyproject.toml`
- `AGENTS.md`

## Allowed paths

```text
.github/workflows/
README.md
```

`pyproject.toml` samo ako je nužno i uz eksplicitno obrazloženje.

## Forbidden paths

```text
src/
desktop/
backend/
web/
migrations/
```

## Required workflow

Minimalno:

```text
checkout
setup-python
install dependencies
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

## Important constraint

Ne uvoditi:

- matrix na mnogo Python verzija,
- Docker,
- složen caching,
- coverage gate ako nije projektni standard.

## Acceptance criteria

- workflow se pokreće na `push` i `pull_request`,
- sve tri provjere prolaze na trenutnom `main`,
- CI koristi Python verziju usklađenu sa projektom,
- README kratko navodi CI.

## Verification

- GitHub Actions run = green,
- lokalni testovi i dalje prolaze.

---

# 4. DENT-IMPROVE-003 — Centralizovati runtime/data/resource putanje

**Risk:** MEDIUM  
**Tip:** desktop/platform hardening  
**Prioritet:** A3

## Problem

Desktop trenutno koristi `AppointmentService.from_sqlite("dentaland.db")`, pa baza zavisi od current working directory-ja. Resursi se pronalaze relativno prema source tree-u.

## Objective

Uvesti jedno mjesto koje definiše:

- data directory,
- database path,
- config directory,
- log directory,
- backup directory,
- resource path.

## Proposed file

```text
src/dentaland/paths.py
```

## Read first

- `desktop/app.py`
- `desktop/views/main_window.py`
- `desktop/views/sidebar.py`
- `src/dentaland/backup.py`
- `scripts/dev_local.py`
- `.gitignore`
- relevantne testove

## Suggested behavior

Instalirana aplikacija treba koristiti user data folder, npr.:

```text
%LOCALAPPDATA%/Dentaland/
```

Ne hardkodirati Program Files kao mjesto za bazu.

## Allowed paths

```text
src/dentaland/paths.py
desktop/app.py
desktop/views/main_window.py
desktop/views/sidebar.py
src/dentaland/backup.py
tests/
README.md
```

## Forbidden changes

- ne mijenjati DB schema,
- ne mijenjati booking behavior,
- ne uvoditi novi config framework,
- ne praviti system service.

## Acceptance criteria

- database path više ne zavisi implicitno od cwd-a u normalnom desktop runu,
- development workflow kroz `scripts/dev_local.py` ostaje jednostavan,
- resource loading radi kroz centralni helper,
- testovi mogu override-ovati paths,
- worktree testovi ne koriste zajedničku produkcijsku bazu.

## Verification

- unit test za path resolution,
- desktop smoke test,
- `pytest`,
- `ruff`,
- `mypy`.

---

# 5. DENT-IMPROVE-004 — Implementirati „Blokiraj vrijeme“

**Risk:** MEDIUM  
**Tip:** desktop feature  
**Prioritet:** A4

## Problem

Model i servis već imaju `TimeOff`, a kalendar ga može prikazati, ali korisnik nema UI da kreira ili ukloni blokirano vrijeme.

## Objective

Napraviti minimalan operativni workflow za odsustvo/blokadu.

## User flow

```text
Sidebar → Blokiraj vrijeme
→ doktor
→ datum
→ vrijeme od
→ vrijeme do
→ razlog (opciono)
→ Sačuvaj
```

Dodatno:

- prikaz aktivnih/nadolazećih blokada,
- brisanje blokade uz potvrdu.

## Read first

- `src/dentaland/models.py`
- `src/dentaland/services/booking.py`
- `desktop/views/main_window.py`
- `desktop/views/sidebar.py`
- `desktop/views/dialogs/`
- `tests/test_services.py`
- `tests/test_gui/`

## Suggested implementation

Dodati servisne metode:

```text
create_time_off(...)
list_time_off(...)
delete_time_off(...)
```

i poseban QWidget/page ili dijalog.

## Allowed paths

```text
src/dentaland/services/booking.py
desktop/views/
tests/test_services.py
tests/test_gui/
```

Model/migration se ne mijenja osim ako agent dokaže da postojeći `TimeOff` model nije dovoljan.

## Acceptance criteria

- može se kreirati blokada,
- prikazuje se na kalendaru,
- ne može se unijeti `end <= start`,
- može se obrisati,
- blokada drugog doktora ne utiče na pogrešnog doktora,
- postojeći termini nisu tiho obrisani/pomjereni.

## UX requirement

Ako blokada preklapa postojeći termin, aplikacija mora eksplicitno upozoriti korisnika.

## Verification

- service tests,
- GUI tests,
- ručni smoke test,
- full pytest/ruff/mypy.

---

# 6. DENT-IMPROVE-005 — Minimalne Postavke

**Risk:** MEDIUM  
**Tip:** desktop feature  
**Prioritet:** A5

## Problem

Doktori, usluge i radno vrijeme postoje u modelu, ali se aplikacija praktično oslanja na seed podatke.

## Objective

Napraviti samo minimalne postavke potrebne stvarnoj ordinaciji.

## Scope

### Doktori

- lista,
- aktivan/neaktivan.

### Usluge

- naziv,
- trajanje,
- buffer,
- dodavanje/uređivanje.

### Radno vrijeme

- doktor,
- dan u sedmici,
- jedan ili više intervala od/do.

## Explicitly out of scope

- korisnički nalozi,
- RBAC,
- SMTP settings UI,
- cloud settings,
- multi-tenancy,
- branding editor.

## Architecture rule

Business/database operacije ostaju u servisnom sloju. `views/` ne importuje SQLAlchemy direktno.

## Acceptance criteria

- aktivacija/deaktivacija doktora radi bez brisanja istorije,
- promjena trajanja usluge utiče na nove termine,
- radno vrijeme podržava split shift,
- validacija sprečava nelogične intervale,
- postojeći scheduler nastavlja raditi.

## Verification

- service tests,
- GUI tests,
- existing scheduling regression tests,
- full gate.

---

# 7. DENT-IMPROVE-006 — Pretvoriti „Novi zahtjevi“ u pravi ekran

**Risk:** LOW/MEDIUM  
**Tip:** desktop UX  
**Prioritet:** A6

## Problem

Sidebar ima rutu „Novi zahtjevi“, ali vodi na `StubPage("Uskoro")`. Stvarna obrada zahtjeva već postoji kroz `DashboardPanels`.

## Objective

Iskoristiti postojeću logiku i napraviti dedicated requests page.

## Important rule

Ne duplirati business logiku iz `DashboardPanels`.

## Minimum page

```text
Novi zahtjevi
- ime
- telefon/email po potrebi
- traženi datum
- vrijeme kreiranja
- Obradi
```

Akcija `Obradi` koristi postojeći `ProcessRequestDialog`.

## Out of scope

- istorija svih zahtjeva,
- CRM,
- patient profile,
- analytics.

## Acceptance criteria

- sidebar route više nije stub,
- pending count se podudara sa servisom,
- confirm/reject radi,
- nakon obrade lista se osvježi,
- postojeći dashboard panel ne gubi funkcionalnost.

---

# 8. DENT-IMPROVE-007 — Operativni automatski backup

**Risk:** MEDIUM  
**Tip:** reliability / operations  
**Prioritet:** B1

## Problem

Backup engine postoji, ali scheduler koji ga stvarno pokreće nije dio sistema.

## Objective

Napraviti jednostavan, dokaziv način da se backup izvršava dnevno na Windows računaru.

## Preferred approach

Ne uvoditi Celery/Redis/service daemon.

Napraviti CLI, npr.:

```bash
python -m dentaland.backup_cli run
python -m dentaland.backup_cli restore-test
python -m dentaland.backup_cli status
```

i dokumentovati Windows Task Scheduler setup.

## Requirements

- backup ne ostavlja plaintext tmp DB,
- key nije u backup folderu,
- exit code je nenula na failure,
- postoji status posljednjeg uspješnog backupa,
- restore test ne prepisuje aktivnu bazu.

## Acceptance criteria

- ručno pokretanje kreira enkriptovan backup,
- scheduler može pozvati isti CLI,
- restore test prolazi na zasebnoj destinaciji,
- failure je vidljiv korisniku/logu.

---

# 9. DENT-IMPROVE-008 — Scheduler za email podsjetnike

> **STATUS (20.8.2026, provjereno protiv `main`): VEĆ URAĐENO.** Implementirano
> kao `DENT-020` (`backend/reminder_scheduler.py` +
> `send_due_appointment_reminders()`), Codex implementer, Claude review PASS,
> MERGED → INTEGRATION_VERIFIED. Vidi `agent_reports/2026-08-20-DENT-020-codex.md`
> i `2026-08-20-DENT-020-review-claude.md`. Odluka o duplom slanju: prihvaćen
> rizik bez schema izmjene (suprotno acceptance kriterijumu ispod — vidi
> Task Contract za obrazloženje). Ostatak sekcije ostaje kao istorijski
> zapis originalne analize, ne kao otvoren zadatak.

**Risk:** MEDIUM  
**Tip:** notifications / operations  
**Prioritet:** B2

## Problem

`send_appointment_reminder()` postoji, ali nema procesa koji bira termine i poziva funkciju u odgovarajuće vrijeme.

## Objective

Napraviti minimalan scheduler bez message brokera.

## Required decision before code

Eksplicitno definisati:

```text
koliko ranije se šalje podsjetnik?
jednom ili više puta?
kako se sprečava duplikat?
```

## Out of scope

- Viber,
- SMS,
- queue/broker,
- distributed scheduler.

## Acceptance criteria

- isti reminder se ne šalje više puta,
- terminalni/cancelled termini se preskaču,
- nema emaila ako pacijent nema email,
- SMTP failure ne ruši scheduler,
- sadržaj ne uključuje uslugu/doktora.

---

# 10. DENT-IMPROVE-009 — Windows packaging + clean-machine test

**Risk:** MEDIUM  
**Tip:** distribution  
**Prioritet:** B3

## Objective

Napraviti reproducibilan Windows build koji se može pokrenuti na računaru bez development environmenta.

## Dependency

Preporučeno nakon `DENT-IMPROVE-003`.

## Scope

- izabrati PyInstaller ili Nuitka,
- napraviti build config,
- uključiti logo/resurse,
- provjeriti writable data path,
- napraviti clean-machine smoke test.

## Minimum smoke test

1. instalirati/pokrenuti aplikaciju,
2. otvoriti scheduler,
3. kreirati termin,
4. zatvoriti aplikaciju,
5. ponovo otvoriti,
6. potvrditi da podatak postoji,
7. otvoriti print preview,
8. potvrditi da resursi rade.

## Out of scope

- auto-update,
- enterprise deployment,
- telemetry.

## Acceptance criteria

- build ne zavisi od source checkouta,
- baza se piše u user data folder,
- resursi se učitavaju,
- testirana je druga mašina/VM.

---

# 11. DENT-IMPROVE-010 — Objediniti overlap logiku

**Status: DONE, 25.8.2026 (nuspojava REF-01, potvrđeno 26.8.2026).**
`availability.validate_appointment_overlap` je jedina overlap funkcija;
`booking.py`/`requests.py` samo re-eksportuju `OverlapError` klasu, nemaju
sopstvenu logiku. Nikad eksplicitno zatvoren pod ovim ID-jem prije sada.

**⚠️ Naming napomena (26.8.2026):** ID `DENT-IMPROVE-010` je NEZAVISNO
dodijeljen i drugom, potpuno nepovezanom tasku —
`agent_reports/DENT-IMPROVE-010-task-contract.md` (Agent Sensors P0
pilot / Habit Hooks, `scripts/agent_sensors.py`, merge `1ef2889`,
26.8.2026). Ta kolizija je greška u dodjeli broja, otkrivena tek nakon
merge-a — file istorija tog taska NIJE preimenovana (već mergovano,
referencirano u više commit poruka i `CURRENT_STATE.md`). Kad se čita
"DENT-IMPROVE-010" bilo gdje u repou, provjeriti KOJI od dva se misli po
kontekstu (ovaj backlog dokument = overlap logika; `agent_reports/`
task contract = Agent Sensors). Ubuduće provjeriti ovaj dokument PRIJE
dodjele novog DENT-IMPROVE broja da se izbjegne ponavljanje.

**Risk:** MEDIUM  
**Tip:** refactor / domain consistency  
**Prioritet:** C1

## Problem

Overlap provjera postoji i u `booking.py` i u `requests.py`. Dupliranje je prvobitno bilo svjesno zbog paralelnog razvoja, ali sada predstavlja rizik divergencije.

## Objective

Imati jednu domensku funkciju/pravilo za SQLite fazu.

## Constraint

Refactor mora biti behavior-preserving.

## Suggested direction

Mali internal helper/module, npr.:

```text
src/dentaland/services/scheduling_rules.py
```

## Acceptance criteria

- oba pozivna toka koriste isti helper,
- svi postojeći overlap testovi prolaze,
- nema promjene status semantike,
- nema PostgreSQL-specifične logike u ovom tasku.

---

# 12. DENT-IMPROVE-011 — Browser E2E testovi javne forme

**Risk:** MEDIUM  
**Tip:** web quality  
**Prioritet:** C2

## Problem

`web/tests/` su uglavnom statični preview fajlovi, ne pravi browser end-to-end testovi.

## Objective

Dodati mali broj visokovrijednih E2E scenarija.

## Preferred tool

Playwright, osim ako agent nađe objektivan razlog protiv.

## Minimum scenarios

1. valid submit → `201`,
2. required field validation,
3. backend unavailable → jasna poruka,
4. `429` rate limit,
5. `409` conflict kada taj flow postoji,
6. mobile viewport smoke test,
7. privacy link postoji.

## Constraint

Ne pretvarati web u React/Vite projekat samo radi testova.

## Acceptance criteria

- testovi rade protiv lokalnog backend+web setupa,
- mogu se pokrenuti jednom komandom,
- ne koriste stvarne podatke pacijenata.

---

# 13. DENT-IMPROVE-012 — PostgreSQL + DB-level overlap zaštita

**Risk:** HIGH  
**Tip:** architecture / migration  
**Prioritet:** C3 — ne počinjati dok lokalna faza nije spremna

## Objective

Preći sa lokalnog SQLite backend prototipa na planirani PostgreSQL produkcijski model.

## Source of truth

`docs/dentaland-razvojni-plan-v3.1.md`

## Required scope

- PostgreSQL schema,
- `btree_gist`,
- `EXCLUDE USING gist`,
- test migracija na kopiji,
- integrity checks,
- 409 mapping za concurrency konflikt.

## Critical constraints

- ne migrirati prvi put direktno na produkcijskim podacima,
- DB constraint je finalni autoritet za overlap,
- manual override ne smije zaobići fizički overlap ako plan nije promijenjen.

## Required evidence

- migration dry-run,
- row count comparison,
- conflict tests,
- rollback plan,
- dva nezavisna reviewera,
- human approval.

## Status napomena (27.8.2026)

Implementacija u toku, `task/DENT-IMPROVE-012-postgres-migration` grana,
čeka review. Obim je Radovanovom odlukom **podijeljen** u odnosu na "Required
scope" gore — `btree_gist`/`EXCLUDE USING gist` namjerno NIJE dio ove
implementacije (odvojen, budući, eksplicitno blokiran task zbog otvorenog
pravnog pitanja u `CLAUDE.md` sekciji "Otvorena pitanja"). Ova implementacija
pokriva: `DATABASE_URL` konekciju, Alembic migraciju na Postgres, migracioni
skript SQLite→Postgres testiran na sintetskim podacima, i potvrdu da
aplikaciona overlap zaštita (`validate_appointment_overlap`) i dalje radi
nad Postgres. Vidi `agent_reports/2026-08-27-DENT-IMPROVE-012-postgres-migration.md`
za punu evidenciju. Otkriven i eskaliran (van scope-a implementera):
`dentaland.db` u glavnom repou sadrži stvaran (ne sintetski) pacijentski
zapis — vidi taj izvještaj za detalje, Radovan treba odlučiti sudbinu tog
fajla.

---

# 14. DENT-IMPROVE-013 — Autentifikacija + RBAC

**Risk:** HIGH  
**Tip:** security  
**Prioritet:** C4

## Objective

Prije javnog izlaganja backenda uvesti individualne naloge i server-side autorizaciju.

## Roles

```text
RECEPTION
DENTIST
ADMIN
```

## Requirements

- individualni nalozi,
- siguran password hashing,
- session/token strategija,
- login rate limiting,
- authorization server-side,
- bez shared admin naloga.

## Out of scope

- OAuth/social login,
- SSO,
- enterprise IAM.

## Acceptance criteria

- neautorizovani korisnik ne može pozvati privileged endpoint,
- svaka uloga ima minimalne potrebne privilegije,
- auth testovi pokrivaju denial cases,
- HIGH security review prolazi.

---

# 15. DENT-IMPROVE-014 — Append-only audit log

**Risk:** HIGH  
**Tip:** compliance / security  
**Prioritet:** C5

## Objective

Uvesti audit događaje odvojene od `updated_at`.

## Minimum events

```text
LOGIN_SUCCESS
LOGIN_FAILURE
CREATE_APPOINTMENT
UPDATE_APPOINTMENT
CANCEL_APPOINTMENT
DELETE_APPOINTMENT
CHANGE_ROLE
```

## Constraints

Audit ne smije sadržati:

- lozinke,
- tokene,
- medicinske bilješke,
- kompletne request body-je.

## Acceptance criteria

- ko/šta/kada se može rekonstruisati za privileged radnje,
- audit zapis se ne mijenja kroz normalan app flow,
- testovi pokrivaju najvažnije akcije.

---

# 16. DENT-IMPROVE-015 — Produkcijski security/privacy release gate

**Risk:** HIGH  
**Tip:** release readiness  
**Prioritet:** C6

## Objective

Dokazati da su uslovi za javni booking ispunjeni.

## Source of truth

Checklist iz:

```text
docs/dentaland-razvojni-plan-v3.1.md
```

## Minimum gate

Potvrditi:

- HTTPS,
- auth,
- RBAC,
- audit,
- rate limiting,
- minimalnu javnu formu,
- privacy notice,
- backup + restore,
- token sigurnost,
- breach runbook,
- retention dokument,
- processor evidenciju,
- produkcijske podatke van AI/dev dumpova,
- PostgreSQL concurrency protection.

## Required output

```yaml
verdict: PASS | REJECT
blocking_findings:
evidence:
open_risks:
```

---

# 17. Zadaci koje NE preporučujem sada

## Patient CRM modul

Ne graditi prije stvarne potvrđene potrebe.

## Reports/analytics modul

Ne graditi bez konkretnog pitanja koje ordinacija želi odgovoriti.

## Multi-tenancy

Nema drugog stvarnog klijenta.

## Plugin sistem

Nema potvrđenih extension pointova.

## Redis / message broker

Nije potreban za trenutni obim.

## Cloud sandbox infrastruktura

Nije dio Dentaland produkcijskog problema.

## Kompleksan FlowOS integration task

Agent-ready sloj već radi ručno. FlowOS kasnije treba automatizovati dokazani proces.

---

# 18. Predložena zavisnost taskova

```text
DENT-IMPROVE-001  Context cleanup

DENT-IMPROVE-002  CI

DENT-IMPROVE-003  Paths/resources
        │
        ├──> DENT-IMPROVE-007 Backup scheduler
        └──> DENT-IMPROVE-009 Windows packaging

DENT-IMPROVE-004  Block time
DENT-IMPROVE-005  Settings
DENT-IMPROVE-006  Requests page
DENT-IMPROVE-008  Reminder scheduler

--------------------------------
LOCAL OPERATIONAL MILESTONE
--------------------------------

DENT-IMPROVE-010  Shared overlap rule — DONE (25.8.2026, REF-01 nuspojava)
DENT-IMPROVE-011  Web E2E — DONE (26.8.2026, merge f9de00e)
        │
        └──> DENT-IMPROVE-012 PostgreSQL — DONE (27.8.2026, merge 824590f)
                    │
                    ├──> DENT-IMPROVE-013 Auth/RBAC — sad jedini neblokiran Prioritet C task
                    ├──> DENT-IMPROVE-014 Audit
                    └──> DENT-IMPROVE-015 Production gate
```

**Napomena o paralelizaciji (26.8.2026):** pošto je 010 već gotov, 011 je
JEDINI Prioritet C task bez otvorene zavisnosti — 012/013/014/015 svi
eksplicitno čekaju 011. Unutar 011 samog nema čistog zero-overlap
razdvajanja za dva nezavisna implementera (jedan dijeljen Playwright
harness/scaffolding, acceptance eksplicitno traži "mogu se pokrenuti
jednom komandom") — ne forsirati paralelizam gdje dependency graph i
sam dijeljeni setup to ne dozvoljavaju.

---

# 19. Preporučeni prvi paket za agente

## Agent A

```text
DENT-IMPROVE-001
Context Debt cleanup
```

## Agent B

```text
DENT-IMPROVE-002
GitHub Actions CI
```

## Agent C

```text
DENT-IMPROVE-003
Runtime/data/resource paths
```

Nakon toga:

## Agent D

```text
DENT-IMPROVE-004
Block time
```

## Agent E

```text
DENT-IMPROVE-006
Requests page
```

`DENT-IMPROVE-005` Settings je bolje raditi nakon Block Time taska jer oba diraju navigaciju i dio servisnog sloja.

---

# 20. Standardni prompt za dodjelu bilo kojeg taska

```text
Implementiraj task <TASK_ID> iz dokumenta
DENTALAND_IMPROVEMENT_BACKLOG.md.

Prvo:
1. Pročitaj AGENTS.md.
2. Pročitaj CLAUDE.md.
3. Koristi .agent/PROJECT_MAP.md i .agent/TASK_ROUTING.md.
4. Kreiraj ili potvrdi Task Contract.
5. Radi isključivo u zasebnom worktree-u.

Poštuj:
- risk tier taska,
- allowed/forbidden paths iz taska,
- postojeću Dentaland arhitekturu,
- bez nepovezanog refaktora,
- bez scope expansiona.

Prije završetka:
- pokreni navedenu verifikaciju,
- napiši agent_report,
- navedi changed files,
- navedi test/lint/mypy rezultate,
- navedi unresolved risks,
- status mora biti IMPLEMENTATION_COMPLETE / VERIFICATION_PENDING,
  ne finalni PASS.
```

---

# 21. Konačna preporuka

Najveća vrijednost sada nije u još jednom velikom arhitektonskom redizajnu.

Preporučeni slijed:

```text
očisti context
→ automatizuj CI
→ stabilizuj Windows putanje
→ završi stvarne operativne GUI funkcije
→ automatizuj backup/reminders
→ napravi distributivni build
→ pusti lokalnu stvarnu upotrebu
→ tek onda javni PostgreSQL/auth/audit sloj
```

Glavni kriterij prioriteta:

> **Da li ovaj task približava aplikaciju pouzdanoj svakodnevnoj upotrebi u ordinaciji bez nepotrebnog širenja scope-a?**

Ako je odgovor „ne“, task vjerovatno još nije prioritet.
