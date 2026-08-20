---
task_id: DENT-IMPROVE-003
risk: MEDIUM
implementer: pi
reviewers: [claude]
verdict: PASS_WITH_NOTES
created_at: 2026-08-20
---

# DENT-IMPROVE-003 — nezavisan review (Claude)

## Metod

Nezavisna provjera od nule (`independent-review` skill) — Pi-jev
izvještaj (`agent_reports/2026-08-20-DENT-IMPROVE-003-pi.md`) tretiran
kao tvrdnja, ne dokaz. Sve niže je nezavisno rekonstruisano, ponovo
pokrenuto i live testirano u worktree-u
`Dentaland-worktrees/DENT-IMPROVE-003-paths`
(`task/DENT-IMPROVE-003-paths`, granat od `main` `07449cc`).

## Administrativna napomena (ne utiče na verdikt)

Task Contract front matter navodi `implementer: crush`, ali Radovan je
zadatak usmeno dodijelio Pi-ju. Pi je to transparentno naveo u svom
reportu bez da dira Task Contract (nije u `allowed_paths`) — ispravno
ponašanje. Ažuriram front matter na `implementer: pi` u ovom review-u.

## Scope

```text
git diff --stat
 README.md                    |  8 ++
 desktop/app.py               | 20 +++++-
 desktop/views/main_window.py |  6 +-
 desktop/views/sidebar.py     |  6 +-
 tests/test_gui/test_app.py   | 19 ++++-
+ src/dentaland/paths.py (novo)
+ tests/test_paths.py (novo)
```

Svi fajlovi su unutar `allowed_paths`. `src/dentaland/backup.py` je bio
dozvoljen ali namjerno nedirnut (već prima putanje eksplicitno kroz
`BackupConfig`) — provjereno, tačno. `scripts/dev_local.py`, DB schema,
booking logika, `backend/` — nedirani, potvrđeno kroz `git diff --stat`.

## Verdikt: PASS_WITH_NOTES

### Acceptance

| Kriterij | Status | Dokaz |
|---|---|---|
| db path ne zavisi implicitno od cwd-a (instalirana app) | PASS | live proba u ovom worktree-u: `paths.database_path()` bez override → `C:\Users\...\AppData\Local\Dentaland\dentaland.db` (pravi `%LOCALAPPDATA%`, ne cwd) |
| dev workflow (`scripts/dev_local.py`) ostaje jednostavan | PASS | `_resolve_db_path()` u `desktop/app.py` čita cwd `dentaland.db` prvo — pošto `dev_local.py` pokreće desktop sa `cwd=ROOT`, ponašanje je nepromijenjeno; fajl nije diran |
| resource loading kroz centralni helper | PASS | `main_window.py`/`sidebar.py` sada zovu `paths.resource_path(...)`; live proba potvrđuje da pokazuje na postojeći `web/assets/logo.png` u ovom checkout-u |
| testovi mogu override-ovati paths | PASS | `data_dir()`/`database_path()`/itd. primaju eksplicitan `env: Mapping\|None` parametar (dependency injection), ne čitaju `os.environ` direktno u testovima |
| worktree testovi ne koriste zajedničku produkcijsku bazu | PASS, provjereno adversarno | tražio sam scenario gdje bi test slučajno pisao u pravi `%LOCALAPPDATA%\Dentaland\` — nije nađen: `test_main_otvara_prozor_maksimizovan` monkeypatch-uje `_resolve_db_path` direktno; oba nova `_resolve_db_path` testa koriste `monkeypatch.chdir(tmp_path)` + `tmp_path`/`DENTALAND_DATA_DIR` override, nikad pravi env |

### Reprodukcija (nezavisna, ne prepisana)

```text
pytest tests/ -q → 229 passed, 11 warnings (identično Pi-jevoj tvrdnji)
ruff check src/dentaland desktop backend tests → All checks passed
mypy src/dentaland desktop backend → Success, 32 source files
git diff --check → prazan izlaz (PASS)

Live proba (ova mašina, bez override):
data_dir()      → C:\Users\38765\AppData\Local\Dentaland
database_path() → C:\Users\38765\AppData\Local\Dentaland\dentaland.db
resource_path() → .../DENT-IMPROVE-003-paths/web/assets/logo.png (is_file: True)
data_dir override → C:/temp/xyz (poštovan)
```

### Pokušaj obaranja (Korak 4)

Tražio sam: test koji poziva `desktop.app.main()` ili kreira `MainWindow`
bez izolacije od pravog user data foldera — nije nađen, svi GUI/app
testovi monkeypatch-uju `_resolve_db_path` ili `chdir`/`DENTALAND_DATA_DIR`
kroz `tmp_path`. Provjerio `mkdir(parents=True, exist_ok=True)` prije
otvaranja baze — pokriva prvi-put-pokretanje na čistoj instalaciji bez
postojećeg `%LOCALAPPDATA%\Dentaland\` foldera. Provjerio da
`resource_path()` koristi `Path(__file__).resolve().parents[2]` relativno
na `paths.py` lokaciju unutar OVOG worktree-a, ne neki drugi checkout —
live proba potvrđuje tačan, postojeći fajl.

### `OUT_OF_SCOPE_FINDING` — provjereni, oba tačna

Nezavisno potvrđeno grep-om, ne samo prepisano iz izvještaja:

1. `desktop/print_document.py:21` (`parents[1]`) i
   `desktop/views/dialogs/base_dialog.py:25` (`parents[3]`) — obje i
   dalje imaju hardkodovanu source-tree resource putanju do loga.
   Potvrđeno: nijedan od ta dva fajla nije u `allowed_paths` ovog taska,
   pa je ispravno da ih implementer nije dirao (bilo bi scope creep).
   Slažem se sa predlogom: zaseban LOW follow-up.
2. `backend/main.py:56` — `os.environ.get("DENTALAND_DB_PATH", "dentaland.db")`,
   potvrđeno tačno. Dva paralelna mehanizma (`DENTALAND_DB_PATH` fajl-nivo
   vs novi `DENTALAND_DATA_DIR` folder-nivo) postoje namjerno — backend
   nije bio u scope-u. Slažem se da ujedinjavanje čeka na task koji dira
   backend hosting/packaging.

### `blocking_findings`

Nijedan.

## Probni signal — `.agent/` sloj (potvrđeno protiv Pi-jevog izvještaja)

Konzistentno sa stvarnim scope-om koji sam nezavisno provjerio. Prvi test
na desktop path/infrastructure tipu zadatka (različit od CI/tooling u
DENT-IMPROVE-002 i servisnih taskova ranije) — Pi je koristio postojeći
kontekst iz prethodnog zadatka (`.agent/PROJECT_MAP.md`/`TASK_ROUTING.md`
učitani ranije u DENT-IMPROVE-002) plus ciljano grep-ovao cwd/resource
zavisnosti — nije bilo repo-wide lutanja, i zadržao je čist scope uprkos
MEDIUM riziku koji dira produkcijski kod (ne samo dokumentaciju/CI).

## Integration status

`REVIEWED → PASS_WITH_NOTES` — čeka Radovanov human approval (MEDIUM
risk), zatim merge i post-merge integration gate na `main`.

## Handoff

CILJ: centralno mjesto za sve runtime/data/resource putanje; instalirana
app → `%LOCALAPPDATA%/Dentaland/`.

URAĐENO: PASS_WITH_NOTES — implementacija ispravna, scope čist, test
izolacija adversarno provjerena (nijedan test ne dira pravi user data
folder), live ponašanje potvrđeno na stvarnom sistemu. Nema blocking
findings.

NE DIRATI: `scripts/dev_local.py`, `src/dentaland/backup.py`, DB schema,
booking logika, `backend/` — nisu dirani, van scope-a.

SLJEDEĆE: Radovanov human approval → merge → post-merge integration gate
na `main`. Nakon toga `DENT-IMPROVE-004` (Block time) — koordinaciona
napomena iz Task Contracta i dalje važi: 004 dira iste navigacione
fajlove, pokrenuti tek nakon merge-a ovog taska. Dva
`OUT_OF_SCOPE_FINDING` ostaju otvorena kao mogući budući LOW follow-up
taskovi.
