---
task_id: DENT-IMPROVE-003
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-20
---

# DENT-IMPROVE-003 — Centralizovati runtime/data/resource putanje

> Napomena: Task Contract front matter kaže `implementer: crush`, ali
> Radovan je ovaj zadatak dodijelio meni (pi). Nisam mijenjao Task Contract
> fajl (nije u `allowed_paths`) — samo navodim da implementaciju radi pi.

## Probni signal — `.agent/` navigacioni sloj (zabilježeno prije prve izmjene koda)

- **Fajlova pročitanih prije 1. izmjene koda: 10** read pozivom u ovom
  zadatku: `agent_reports/DENT-IMPROVE-003-task-contract.md`,
  `.agent/CURRENT_STATE.md`, `desktop/app.py`,
  `desktop/views/main_window.py`, `desktop/views/sidebar.py`,
  `src/dentaland/backup.py`, `scripts/dev_local.py`,
  `tests/test_gui/test_app.py`, `tests/test_backup.py`, `README.md`.
  Dodatno, iz prethodnog zadatka (DENT-IMPROVE-002) već su bili u
  kontekstu: `CLAUDE.md`, `.agent/PROJECT_MAP.md`, `.agent/TASK_ROUTING.md`,
  `docs/DENTALAND_IMPROVEMENT_BACKLOG.md` (sekcija 4),
  `docs/dentaland-agentski-razvoj.md`.
- Koristio `.agent/PROJECT_MAP.md`: **DA** — "Entry points" je odmah pokazao
  `desktop/app.py`; "Booking domain" / "Desktop scheduler" sekcije su
  usmjerile na `services` i `desktop/views/`.
- Koristio `.agent/TASK_ROUTING.md`: **DA** — Desktop GUI routing paket je
  zadržao read-set na `desktop/` + relevantnim testovima; nisam učitavao
  `backend/`/`web/`/`migrations/`.
- Tražio dodatno pojašnjenje strukture: **DA, ciljano** — grep za sve
  lokacije `dentaland.db`/`from_sqlite`/`parents[2]`/`logo.png` (da nađem
  sve cwd/resource zavisnosti), provjera `web/assets/logo.png` postoji, i
  `git diff ae7bf53..HEAD` da potvrdim da ciljni fajlovi nisu mijenjani
  DENT-IMPROVE-002 merge-om. Nije bilo repo-wide `ls`/`find` lutanja.
- Ostao u `allowed_paths`: **DA** — planirane izmjene su isključivo
  `src/dentaland/paths.py` (novi), `desktop/app.py`,
  `desktop/views/main_window.py`, `desktop/views/sidebar.py`, `tests/`,
  `README.md`. `src/dentaland/backup.py` je u `allowed_paths`, ali ga nije
  trebalo mijenjati (vidi "Šta je urađeno").

## Task Contract

Izvor: `agent_reports/DENT-IMPROVE-003-task-contract.md` (puni detalj u
`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 4).

Cilj: uvesti jedno mjesto (`src/dentaland/paths.py`) koje definiše data
directory, database path, config directory, log directory, backup
directory i resource path — instalirana aplikacija koristi user data
folder (`%LOCALAPPDATA%/Dentaland/`), ne Program Files. MEDIUM risk; jedan
nezavisan reviewer (Claude).

**Allowed paths:** `src/dentaland/paths.py`, `desktop/app.py`,
`desktop/views/main_window.py`, `desktop/views/sidebar.py`,
`src/dentaland/backup.py`, `tests/`, `README.md`.

**Forbidden:** DB schema, booking behavior, novi config framework, system
service.

## Scope

- `src/dentaland/paths.py` — novi modul: `data_dir()`, `database_path()`,
  `config_dir()`, `log_dir()`, `backup_dir()`, `resource_path()`.
- `desktop/app.py` — `main()` koristi `_resolve_db_path()` umjesto
  hardkodovanog `"dentaland.db"`.
- `desktop/views/main_window.py` — logo ikona kroz `paths.resource_path()`.
- `desktop/views/sidebar.py` — logo kroz `paths.resource_path()`.
- `tests/test_paths.py` — novi unit testovi za path resolution.
- `tests/test_gui/test_app.py` — ažuriran test `main()` + novi testovi za
  `_resolve_db_path()`.
- `README.md` — kratka napomena gdje instalirana app čuva podatke.

Netaknuto: `src/dentaland/backup.py` (već prima eksplicitne putanje kroz
`BackupConfig`, nema implicitne cwd zavisnosti — nije trebalo mijenjati).

## Šta je urađeno

### `paths.py` — centralne putanje

- `data_dir()`: `DENTALAND_DATA_DIR` env var (eksplicitni override →
  testovi mogu override-ovati paths), pa platform default:
  Windows `%LOCALAPPDATA%/Dentaland`, macOS
  `~/Library/Application Support/Dentaland`, Linux `~/.local/share/dentaland`.
- `database_path()` = `data_dir() / "dentaland.db"` — čista funkcija, bez
  cwd magije (dev fallback je namjerno u `desktop/app.py`, ne ovdje, da
  testovi mogu pouzdano override-ovati).
- `config_dir()`, `log_dir()`, `backup_dir()` — podfolderi `data_dir()`.
- `resource_path()`: source checkout → repo root (`parents[2]` od
  `src/dentaland/paths.py`); PyInstaller bundle (`sys._MEIPASS`, budući
  DENT-IMPROVE-009) → bundle root.

### `desktop/app.py` — database path

`_resolve_db_path()`: ako `dentaland.db` postoji u cwd (dev kroz
`scripts/dev_local.py`, koji pokreće desktop sa `cwd=ROOT` i dijeli bazu
sa backendom), koristi taj fajl; inače `paths.database_path()`
(instalirana app → user data folder). Ovako development workflow ostaje
nepromijenjen bez ikakve izmjene `scripts/dev_local.py` (nije u
`allowed_paths`).

### Resursi

`main_window.py` i `sidebar.py` sada učitavaju logo kroz
`paths.resource_path("web", "assets", "logo.png")` umjesto ručnog
`Path(__file__).resolve().parents[2] / "web" / "assets" / "logo.png"`.

## Tehničke odluke

### Zašto dev fallback živi u `desktop/app.py`, ne u `paths.py`

Da `database_path()` ostane čista i predvidljiva: testovi je mogu
override-ovati kroz `DENTALAND_DATA_DIR` bez rizika da `dentaland.db` iz
repo root-a (koji postoji u glavnom checkout-u) "otme" putanju. Dev vs
prod je politika desktop entrypointa, ne svojstvo centralnog modula.

### `scripts/dev_local.py` se ne dira

Nije u `allowed_paths`. Kompatibilnost se postiže isključivo čitanjem
postojećeg ponašanja (`cwd=ROOT` + `dentaland.db` u ROOT) — desktop app u
dev modu pronađe tu bazu i nastavi da je dijeli sa backendom.

### `backup.py` se ne dira

Već prima sve putanje eksplicitno kroz `BackupConfig` — nema implicitne
cwd zavisnosti koju bi ovaj task trebao ukloniti. Centralna `backup_dir()`
u `paths.py` postoji za buduće pozivaoce (DENT-IMPROVE-007 scheduler).

### `DENTALAND_DATA_DIR` (novo) vs `DENTALAND_DB_PATH` (postojeće u backendu)

Backend već ima `DENTALAND_DB_PATH` za direktan db fajl. `paths.py` uvodi
`DENTALAND_DATA_DIR` (folder-nivo, od čega je baza samo jedan dio). Nisu
ujedinjavani jer backend nije u scope-u — zabilježeno kao OUT_OF_SCOPE.

## Verifikacija (rezultati)

```text
git diff --check
→ PASS, exit 0

ruff check src/dentaland desktop backend tests
→ All checks passed, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 32 source files, exit 0

pytest tests/ -q
→ 229 passed, 11 warnings, exit 0
   (222 baseline + 5 tests/test_paths.py + 2 nova test_app.py)
```

Desktop smoke (offscreen, bez otvaranja stvarne baze):

```text
python -c "MainWindow(FakeStore()) + Sidebar() + paths.resource_path(...)"
→ logo resource .../web/assets/logo.png -> True
→ MainWindow + Sidebar smoke OK
```

Warnings su postojeći dependency deprecation warning-i (httpx/slowapi/alembic),
ne vezani za ovaj task. Pravi vizuelni smoke (otvaranje prozora sa stvarnom
bazom) nije pokrenut u headless okruženju — GUI testovi (offscreen) pokrivaju
kreiranje MainWindow/Sidebar, a `test_paths.py` potvrđuje da resource path
pokazuje na postojeći logo.

## OUT_OF_SCOPE_FINDING

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  Duplirana source-tree resource putanja do loga i dalje postoji u
  desktop/print_document.py (_LOGO_PATH, parents[1]) i
  desktop/views/dialogs/base_dialog.py (_LOGO_PATH, parents[3]) — van
  allowed_paths ovog taska, pa nisu prebačeni na paths.resource_path().
location: desktop/print_document.py:21, desktop/views/dialogs/base_dialog.py:25
risk: LOW
proposed_task: >
  Zaseban LOW task da se te dvije lokacije prebace na paths.resource_path()
  i ukloni preostalo dupliranje resource logike.
```

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  backend/main.py koristi DENTALAND_DB_PATH (direktan db fajl), a novi
  paths.py uvodi DENTALAND_DATA_DIR (folder). Dva mehanizma za putanje —
  nisu ujedinjeni jer backend nije u allowed_paths.
location: backend/main.py:56
risk: LOW
proposed_task: >
  Kasniji task da backend i desktop dijele isti paths modul (kad se bude
  dirao backend hosting/packaging).
```

## Review

`PENDING` — implementer nije reviewer. Potreban je nezavisan Claude review
sa fokusom na scope (allowed/forbidden paths), acceptance kriterijume
(posebno dev workflow + worktree baza) i ispravnost path resolution.

## Integration status

`NOT_MERGED` — čeka nezavisan review i Radovanov human approval (MEDIUM).

## Handoff

CILJ: centralno mjesto za sve runtime/data/resource putanje;
instalirana app → `%LOCALAPPDATA%/Dentaland/`.

URAĐENO: `paths.py` + integracija u `app.py`/`main_window.py`/`sidebar.py`
+ testovi + README napomena.

NE DIRATI: `scripts/dev_local.py`, `src/dentaland/backup.py`, DB schema,
booking behavior.

SLJEDEĆE: Claude radi nezavisan MEDIUM-risk review; nakon PASS-a Radovanov
human approval, pa merge.
