---
task_id: DENT-IMPROVE-010
risk: MEDIUM
implementer: TBD
reviewers: [claude]
status: "OPEN — task contract napisan prije koda"
created_at: 2026-08-26
---

# DENT-IMPROVE-010 — Agent Sensors P0 pilot (arhitektonski guardovi + replay validacija)

## Kontekst

Radovan je odobrio `DENTALAND_NOVI_RADNI_TOK_HABIT_HOOKS.md` (prijedlog
pregledan 26.8.2026, zasnovan na `main` HEAD `42f180d`) za uvrštavanje u
radni tok. Ovaj task pokriva SAMO fazu **A1+A2** iz tog dokumenta (sekcija
23) — izgradnju tri arhitektonska senzora i njihovu validaciju protiv
poznate istorije repoa. **Ne uključuje A3 (CI wiring)** — to ide u
poseban budući task tek ako A2 dokaže da senzor radi (dokument, sekcija
17: "Ako senzor ne može reproducirati poznatu istoriju ili ima mnogo
false positive nalaza, ne stavljati ga u CI").

Motivacija je direktno dokumentovana u repou: finalni acceptance audit
REF-00..08 (`agent_reports/2026-08-25-REF-FINAL-acceptance-review-codex.md`,
`-claude.md`) je pronašao četiri View→Service bypass-a (F1-F4) dok su
pytest/ruff/mypy bili zeleni; REF-09 i REF-11 su oba prošla kroz Codex
REJECT rundu jer postojeći GUI testovi nisu razlikovali novi Controller
put od starog direktnog puta. Cilj ovog taska je da se ta klasa problema
uhvati DETERMINISTIČKI, prije reviewera, ne da se review ukine.

## Cilj (tačno prema prijedlogu, sekcija 6, 9, 10, 17)

### 1. `scripts/agent_sensors.py`

CLI u istom stilu kao `scripts/coordination.py` (argparse, UTF-8 fix za
Windows konzolu, docstring na srpskom/bosanskom). Komande:

```bash
python scripts/agent_sensors.py --changed          # samo git-izmijenjeni fajlovi
python scripts/agent_sensors.py --all               # cijeli relevantan scope
python scripts/agent_sensors.py --changed --json     # mašinski output
```

`--changed` određuje izmijenjene fajlove preko `git diff --name-only` u
odnosu na trenutnu granu (isti pristup kao coordination.py-jev
`--git-common-dir`/`--show-toplevel` obrazac za worktree-svjesnost).

Implementira **tačno tri** AST-bazirana guarda (ne više, dokument sekcija
20/R1 eksplicitno upozorava na "previše pravila prije dokaza koristi"):

**ARCH-VIEW-001** (`desktop/views/**`, severity BLOCK) — traži direktne
pozive `self.store.<mutacija>(...)` gdje je `<mutacija>` u definisanom
skupu (izveden iz F1-F4 nalaza i REF-09..12 rada):

```text
create, update, move, cancel, delete,
mark_confirmed, mark_arrived, unmark_arrived, mark_completed, mark_no_show,
set_doctor_active, add_service, update_service, set_working_hours,
create_time_off, delete_time_off
```

**ARCH-CONTROLLER-001** (`desktop/controllers/**`, severity BLOCK) — traži
SQLAlchemy import, `select(...)`, `Session`, `.execute`/`.commit` pozive.

**ARCH-SERVICE-001** (`src/dentaland/services/**`, severity BLOCK) — traži
`PySide6` import (bilo koji oblik: `import PySide6`, `from PySide6...`).

Svaki nalaz vraća strukturu tačno po dokumentu (sekcija 9):

```json
{
  "code": "ARCH-VIEW-001",
  "severity": "BLOCK",
  "file": "desktop/views/day_view.py",
  "line": 363,
  "signal": "direct mutating store call: self.store.move(...)",
  "rule": "View -> Controller -> Service",
  "guide": "ARCH-VIEW-001"
}
```

Human-readable format tačno po dokumentu (sekcija 11).

### 2. `.agent/HABIT_GUIDES.yaml`

Tri guide-a (ARCH-VIEW-001, ARCH-CONTROLLER-001, ARCH-SERVICE-001), sadržaj
tačno prema dokumentu sekcija 6 (signal/namjera/nemoj-samo/uradi struktura).
Guide NE redefiniše arhitekturu — referencira postojeća pravila
(`docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md` sekcija 3.2),
opisuje samo kako reagovati na konkretan signal (dokument, R4 mitigacija).

### 3. `tests/test_architecture_contracts.py`

**A2 — replay validacija protiv poznate istorije** (dokument sekcija 17,
Test A/B/C). Ovo je SRŽ ovog taska, ne opciona dopuna:

- **Test A**: pokrenuti `ARCH-VIEW-001` na REF-00..08 finalnom stanju
  (commit prije REF-09, npr. `52f57fb`-ovog prethodnika ili tačnije na
  merge-u prije REF-09 — implementer treba naći tačan commit gdje su F1-F4
  još aktivni) — senzor MORA prijaviti sve od 4 poznate lokacije (F1:
  `day_view.py`/`week_view.py`, F2: `blockout_panel.py`, F3:
  `settings_panel.py`, F4: `requests_panel.py`), ni manje ni više
  (provjeriti da nema false positive na ostalim View fajlovima koji su
  već čisti).
- **Test B**: pokrenuti na stanju poslije REF-09+REF-11 merge-a (prije
  REF-10/12) — F4 i F2 lokacije MORAJU nestati iz nalaza, F1
  (`day_view`/`week_view`) i F3 (`settings_panel`) MORAJU ostati vidljivi.
- **Test C**: pokrenuti na TRENUTNOM `main` (poslije REF-09/10/11/12,
  provjeriti da je REF-10 stvarno mergovan prije pokretanja ovog taska) —
  očekivanje: **0 blocking ARCH-VIEW-001 nalaza**.

Kako pristupiti starim commit-ima za replay: `git show <commit>:<path>`
ili privremeni `git worktree add` na stari commit — implementer bira
tehniku, ali test mora biti reproducibilan i ne smije ostaviti prljavo
stanje u glavnom repou (očistiti privremeni worktree na kraju testa).

Ako senzor NE prepozna poznatu F1-F4 istoriju tačno (ni manje ni više),
to je `REJECT` razlog za cijeli task — dokument je eksplicitan: "Ako
senzor ne može reproducirati poznatu istoriju... ne stavljati ga u CI."

### 4. Red Team provjera (dokument sekcija 21, minimalna verzija)

Implementer treba probati barem ove opstrukcije na `ARCH-VIEW-001` i
dokumentovati rezultat u izvještaju (ne mora ih sve pobijediti, ali MORA
znati i napisati granice — dokument: "ne mora verzija 1 hvatati svaku
obfuskaciju, ali moramo znati granice senzora"):

```python
store2 = self.store
store2.move(...)          # alias — očekivano NE hvata (poznato ograničenje)

getattr(self.store, "move")(...)   # dynamic — očekivano NE hvata
```

## Šta OVAJ task NE radi (eksplicitno van scope-a)

- Ne dira CI (`.github/workflows/ci.yml`) — A3 je poseban budući task.
- Ne dodaje `ARCH-TIMEZONE-001` (dokument: aktivirati tek nakon REF-13,
  koji još nije urađen).
- Ne dira `scripts/coordination.py` (poznat postojeći ruff nalaz tamo je
  poseban task, dokument sekcija 16 eksplicitno kaže da se ne širi usput).
- Ne dodaje complexity/smell senzore (S4 iz dokumenta — eksplicitno
  odloženo).
- Ne mijenja Task Contract format niti dodaje `guards:` YAML polje —
  dokument sekcija 2 (D1) kaže da je to opciono TEK ako se pilot pokaže
  korisnim.

## Acceptance

- [ ] `scripts/agent_sensors.py` postoji, radi `--changed`/`--all`/`--json`;
- [ ] `.agent/HABIT_GUIDES.yaml` sadrži tačno tri guide-a;
- [ ] `tests/test_architecture_contracts.py` sadrži Test A/B/C (replay) i
      prolazi;
- [ ] Test A dokazano pronalazi tačno F1-F4 lokacije na REF-00..08 stanju;
- [ ] Test B dokazano pokazuje F2/F4 nestale, F1/F3 još vidljive;
- [ ] Test C dokazano pokazuje 0 blocking nalaza na trenutnom `main`;
- [ ] Red Team rezultati (alias/getattr) dokumentovani u izvještaju, sa
      jasnom izjavom o poznatim ograničenjima senzora;
- [ ] `pytest tests/ -q`, `ruff check src/dentaland desktop backend tests
      scripts/agent_sensors.py`, `mypy src/dentaland desktop backend` čisti
      (napomena: `ruff` scope NE širiti na cijeli repo, dokument sekcija 16).

## Allowed paths

```text
scripts/agent_sensors.py                (novo)
.agent/HABIT_GUIDES.yaml                (novo)
tests/test_architecture_contracts.py    (novo)
agent_reports/**
```

## Forbidden paths

```text
scripts/coordination.py
.github/workflows/ci.yml
desktop/**
src/dentaland/**
backend/**
models.py
migrations/**
```

Nulto preklapanje sa REF-13/REF-14 backlogom — ovaj task ne dira
produkcijski kod uopšte, samo tooling/testove.

## Review

Standardan MEDIUM proces (jedan reviewer, ne REF-paketov dual-review —
ovo nije dio REF-00..08 View/Controller/Services plana). Claude review,
Radovan human approval prije merge-a. Reviewer treba posebno provjeriti
da Test A/B/C replay stvarno testira ISTORIJSKE commit-e (ne trenutno
stanje pod drugim imenom) i da su brojevi nalaza tačni, ne približni.

## Koordinacija

Nema zavisnosti od REF-13/REF-14 — može krenuti odmah, paralelno sa bilo
kojim od njih ako je potrebno (nulto preklapanje fajlova).
