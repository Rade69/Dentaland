---
task_id: DENT-IMPROVE-003
risk: MEDIUM
implementer: pi
reviewers: [claude]
verdict: PASS_WITH_NOTES
status: MERGED_INTEGRATION_VERIFIED
commits: [db5f129]
created_at: 2026-08-20
---

## Integration status

`MERGED → INTEGRATION_VERIFIED → DONE` (20.8.2026). Review: Claude
`PASS_WITH_NOTES` (`agent_reports/2026-08-20-DENT-IMPROVE-003-review-claude.md`).
Human approval: Radovan ("Komitj uz ispravku u merdžuj"). Merge commit na
`main` (`--no-ff`). Post-merge gate: `pytest` → 229 passed, `ruff` → All
checks passed, `mypy` → 0 grešaka (32 fajlova). Dva `OUT_OF_SCOPE_FINDING`
ostaju otvorena kao mogući budući LOW follow-up taskovi (logo putanja u
`print_document.py`/`base_dialog.py`; backend `DENTALAND_DB_PATH` vs
`DENTALAND_DATA_DIR`).

# DENT-IMPROVE-003 — Centralizovati runtime/data/resource putanje

## Task Contract

**Cilj:** Desktop trenutno koristi `AppointmentService.from_sqlite("dentaland.db")`,
pa baza zavisi od current working directory-ja, a resursi se pronalaze
relativno prema source tree-u. Uvesti jedno mjesto koje definiše data
directory, database path, config directory, log directory, backup
directory, resource path — instalirana aplikacija treba koristiti user
data folder (npr. `%LOCALAPPDATA%/Dentaland/`), ne hardkodirati Program
Files.

**Risk:** MEDIUM

**Izvor:** `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 4
(`DENT-IMPROVE-003`) — pun detalj tamo, ali prvo pokušaj sam kroz
`AGENTS.md`/`CLAUDE.md` → `.agent/PROJECT_MAP.md`/`.agent/TASK_ROUTING.md`
odrediti šta ti treba; backlog koristi tek ako ti nešto ostane nejasno.

**Proposed file:** `src/dentaland/paths.py`

**Allowed paths:** `src/dentaland/paths.py`, `desktop/app.py`,
`desktop/views/main_window.py`, `desktop/views/sidebar.py`,
`src/dentaland/backup.py`, `tests/`, `README.md`.

**Forbidden:** ne mijenjati DB schema, ne mijenjati booking behavior, ne
uvoditi novi config framework, ne praviti system service.

**Acceptance:**
- database path više ne zavisi implicitno od cwd-a u normalnom desktop runu,
- development workflow kroz `scripts/dev_local.py` ostaje jednostavan,
- resource loading radi kroz centralni helper,
- testovi mogu override-ovati paths,
- worktree testovi ne koriste zajedničku produkcijsku bazu.

**Verification:** unit test za path resolution, desktop smoke test,
`pytest`, `ruff`, `mypy`.

**Review:** Claude, nezavisan od implementera.

## Koordinacija — obavezno prije početka

Ovaj task dira `desktop/views/main_window.py` i `desktop/views/sidebar.py`,
iste fajlove koje diraju i `DENT-IMPROVE-004`/`005`/`006`. Radovan namjerno
ovaj task dodjeljuje PRVI i SOLO — ne raditi paralelno sa 004/005/006 dok
ovaj ne bude MERGED. Koristi `scripts/coordination.py claim` na početku.

## Probni signal — obavezno u `agent_report`

Prije prve izmjene, kratko zapiši: koliko fajlova si pročitao prije prve
izmjene, da li si koristio `.agent/PROJECT_MAP.md`/`.agent/TASK_ROUTING.md`,
da li si tražio dodatno pojašnjenje strukture, da li si ostao u
`allowed_paths`. Nastavak mjerenja iz
`agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md` — prvi
test na desktop path/infrastructure tipu zadatka.
