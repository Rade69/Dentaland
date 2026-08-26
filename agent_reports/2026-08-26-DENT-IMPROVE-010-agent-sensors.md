---
task_id: DENT-IMPROVE-010
risk: MEDIUM
implementer: crush
reviewers: [claude]
status: "READY FOR REVIEW — implementacija + replay validacija + Red Team gotovi (372 pytest, ruff, mypy čisti). NIJE commitovano."
created_at: 2026-08-26
---

# DENT-IMPROVE-010 — Agent Sensors P0 pilot (implementer izvještaj)

## Šta je urađeno (A1 + A2)

### 1. `scripts/agent_sensors.py` (novo)

CLI (`--changed`/`--all`/`--json`) u stilu `coordination.py` (argparse,
UTF-8 fix za Windows, docstring na srpskom). Tri AST guarda:

- **ARCH-VIEW-001** (`desktop/views/**`) — traži `self.store.<mutacija>(...)`
  gdje je `<mutacija>` u definisanom skupu (iz F1-F4).
- **ARCH-CONTROLLER-001** (`desktop/controllers/**`) — SQLAlchemy import,
  `select(...)`, `Session(...)`, `.execute`/`.commit`.
- **ARCH-SERVICE-001** (`src/dentaland/services/**`) — `PySide6` import.

Strukturisan JSON nalaz tačno po dokumentu (sekcija 9). Human-readable format
po sekciji 11.

### 2. `.agent/HABIT_GUIDES.yaml` (novo)

Tri guide-a (signal/namjera/nemoj-samo/uradi struktura), referenciraju
`docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md` sekcija 3.2 (R4
mitigacija — ne redefinišu arhitekturu).

### 3. `tests/test_architecture_contracts.py` (novo)

Replay validacija (A2) + Red Team. Pinovani commit SHA-ovi radi
reproducibilnosti.

## Replay rezultati (tačni brojevi)

Commit SHA pinovani kroz `git log --first-parent`:

| Test | Commit | Šta očekivano | Rezultat |
|---|---|---|---|
| A | `ce2d270` (REF-08 merge) | F1-F4 svi aktivni | **5 fajlova**: day_view, week_view, blockout_panel, settings_panel, requests_panel |
| B | `a87d423` (REF-11 merge) | F2/F4 nestali, F1/F3 ostaju | **3 fajla**: day_view, week_view, settings_panel |
| C | `HEAD` (trenutni main) | — | **2 fajla**: day_view, week_view (F1) |

**Test A** (tačno F1-F4, ni manje ni više):
```text
desktop/views/day_view.py       (F1: store.move)
desktop/views/week_view.py      (F1: store.move)
desktop/views/blockout_panel.py (F2: create_time_off/delete_time_off)
desktop/views/settings_panel.py (F3: 4 settings mutacije)
desktop/views/requests_panel.py (F4: cancel/mark_confirmed)
```

**Test B** (F2/F4 nestali, F1/F3 ostaju):
```text
desktop/views/day_view.py       (F1 — ostaje, REF-10 još nije)
desktop/views/week_view.py      (F1)
desktop/views/settings_panel.py (F3 — ostaje, REF-12 još nije)
```

**Test C** (trenutni main):
```text
desktop/views/day_view.py       (F1)
desktop/views/week_view.py      (F1)
```

## OUT_OF_SCOPE / važan nalaz (prijavljen Radovanu prije koda)

**REF-10 nije mergovan u main** — `git log --first-parent` nema
`task/REF-10-scheduler-drag-drop` merge, a `day_view.py:363` i
`week_view.py:474` i dalje imaju `self.store.move(...)` (F1 aktivan; Pi ga
radi paralelno). Zbog toga Test C NIJE "0 nalaza" kako kontrakt pretpostavlja,
nego **2 nalaza (F1)**. Test C je implementiran sa tačnim očekivanjem (F1
ostaje) i eksplicitnim komentarom da se ažurira na prazan skup kad REF-10 uđe
u main.

## Red Team rezultati (sekcija 21, minimalna verzija)

Na `ARCH-VIEW-001` probane opstrukcije:

```text
1. self.store.move(...)                    → HVAĆA (1 nalaz)
2. store2 = self.store; store2.move(...)   → NE hvata (POZNATO ograničenje: alias)
3. getattr(self.store, "move")(...)        → NE hvata (POZNATO ograničenje: dinamika)
```

Ovo je deterministički zaključano u `test_red_team_alias_i_dinamicki_pozivi_se_ne_hvataju`.

**Izjava o granicama senzora:** verzija 1 hvata SAMO direktan, statički
`self.store.<mutacija>(...)` obrazac. Alias (`store2 = self.store`),
dinamički `getattr`, ili preimenovan atribut se NE hvataju — to je namjerno
prihvaćeno za P0 (dokument, sekcija 21: "ne mora verzija 1 hvatati svaku
obfuskaciju, ali moramo znati granice"). Pravo osiguranje protiv tih
obfuskacija je i dalje test koji pada na starom putu + nezavisni review.

## Verifikacija (stvaran output)

```text
$ python -m pytest tests/ -q
372 passed, 11 warnings in 18.74s

$ ruff check src/dentaland desktop backend tests scripts/agent_sensors.py
All checks passed!

$ mypy src/dentaland desktop backend
Success: no issues found in 52 source files

$ python scripts/agent_sensors.py --all --json
[2 ARCH-VIEW-001 nalaza: day_view.py:363, week_view.py:474]
```

## Dirnuti fajlovi

```text
A  scripts/agent_sensors.py
A  .agent/HABIT_GUIDES.yaml
A  tests/test_architecture_contracts.py
A  agent_reports/2026-08-26-DENT-IMPROVE-010-agent-sensors.md
```

Nedirano (forbidden paths poštovan): `scripts/coordination.py`,
`.github/workflows/ci.yml`, `desktop/**`, `src/dentaland/**`, `backend/**`,
`models.py`, `migrations/**`.

## Napomena

NIJE commitovano/pušovano (po instrukciji). Claim oslobođen
(`coordination.py release --task DENT-IMPROVE-010`).

Senzor radi na `python scripts/agent_sensors.py --changed` bez dodatnih
zavisnosti (samo stdlib `ast`).
