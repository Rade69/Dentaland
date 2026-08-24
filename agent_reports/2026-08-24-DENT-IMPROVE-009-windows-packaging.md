---
task_id: DENT-IMPROVE-009
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-24
---

# DENT-IMPROVE-009 — Windows packaging + clean-machine test

## Task Contract

Izvor: `agent_reports/DENT-IMPROVE-009-task-contract.md` (napisan PRIJE koda).
Cilj: reproducibilan Windows build desktop aplikacije (PyInstaller, onedir,
samo desktop) sa uključenim resursima, plus clean-machine smoke test
(simuliran — nema fizičke čiste mašine). MEDIUM risk; jedan nezavisan
reviewer (Claude), human approval obavezan prije merge-a.

## Odluke (zapisane u Task Contractu)

- PyInstaller (ne Nuitka) — standard za PySide6, dovoljno za obim.
- `--onedir` (ne `--onefile`) — pouzdaniji cold-start, manje AV false-positive.
- Samo desktop app — backend/web nisu u obimu (Faza 0).

## Šta je urađeno

1. **`packaging/dentaland.spec`** — PyInstaller spec:
   - `Analysis(['desktop/app.py'])` sa `pathex=[ROOT, ROOT/src]` (oba paketa:
     `desktop` u korijenu, `dentaland` u `src/`);
   - `datas`: `web/assets/` → `web/assets`, `desktop/assets/doctors/` →
     `desktop/assets/doctors` (poklapa se sa `paths.resource_path()` layout-om);
   - `icon=web/assets/dentaland.ico`, `console=False`, `upx=False`,
     `name="Dentaland"`.
2. **`web/assets/dentaland.ico`** — generisano iz `web/assets/logo.png`
   (Pillow, 7 veličina: 16–256px).
3. **`pyproject.toml`** — dodani `pyinstaller>=6.0` i `pillow>=10.0` u
   `[project.optional-dependencies].dev`.
4. **`docs/dentaland-windows-packaging.md`** — build komanda, gdje exe
   završi, clean-machine test koraci (stvarna mašina + simulacija), poznata
   ograničenja (onedir folder, SmartScreen, nema code-signing).
5. **`README.md`** — kratak odjeljak "Windows build (packaging)" + link na
   vodič.

## Changed files

- `packaging/dentaland.spec` — novi PyInstaller spec.
- `web/assets/dentaland.ico` — novi generisani fajl.
- `pyproject.toml` — dev deps (pyinstaller, pillow).
- `docs/dentaland-windows-packaging.md` — novi vodič.
- `README.md` — dopuna.
- `agent_reports/DENT-IMPROVE-009-task-contract.md` + ovaj izvještaj.

`src/dentaland/services/**`, `src/dentaland/models.py`, `migrations/`,
`backend/`, `desktop/views/**` NISU dirani. `resource_path()`,
`_resolve_db_path()` i `desktop/print_document.py` NISU mijenjani — postojeći
kod je radio u bundle-u bez izmjena (vidi "Nalaz" ispod).

## Nalaz tokom rada (stvaran bug, popravljen u build configu, ne u kodu)

Prvi build je imao `pathex=[ROOT]` (bez `src/`), pa je izgrađen exe na
pokretanju bacao `ModuleNotFoundError: No module named 'dentaland'` — PyInstaller
nije mogao analizirati `dentaland` paket jer živi u `src/`. Popravljeno
dodavanjem `str(ROOT / "src")` u `pathex` (izmjena je u `packaging/dentaland.spec`,
dakle unutar allowed_paths — nije dirao nikakav aplikacijski kod).

## Verifikacija (rezultati)

```text
pytest tests/ -q
→ 298 passed, 11 warnings   (baseline, nepromijenjen)

ruff check src/dentaland desktop backend tests
→ All checks passed!, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 37 source files
```

## Stvaran build (tačan tool output, ne parafraza)

```text
pyinstaller packaging/dentaland.spec --noconfirm
...
INFO: Building EXE from EXE-00.toc completed successfully.
INFO: Building COLLECT COLLECT-00.toc completed successfully.
INFO: Build complete! The results are available in: ...\DENT-IMPROVE-009-windows-packaging\dist
```

Bundle inspekcija (resursi fizički prisutni u `_internal`):

```text
dist/Dentaland/Dentaland.exe                       (2 300 305 bytes)
dist/Dentaland/_internal/web/assets/logo.png       (39 989 bytes)
dist/Dentaland/_internal/web/assets/dentaland.ico  (77 881 bytes)
dist/Dentaland/_internal/web/assets/benefit-*.png, boxicons.*, favicon.png
dist/Dentaland/_internal/desktop/assets/doctors/ana.png | ljubo.png | zorka.png
```

## Clean-machine simulacija — stvarno pokretanje exe iz PRAZNOG foldera

`Dentaland.exe` pokrenut iz praznog foldera VAN repoa (bez `src`/`PYTHONPATH`
dostupnih), sa `DENTALAND_DATA_DIR` na svjež scratch folder i
`QT_QPA_PLATFORM=offscreen`:

```text
run_dir:  C:\Users\38765\AppData\Local\Temp\dent009-c0aj591a\run
data_dir: C:\Users\38765\AppData\Local\Temp\dent009-c0aj591a\data
process alive after 12s: True (returncode=None)
db exists: True
db size: 24576
tables: ['appointments', 'doctors', 'services', 'time_off', 'working_hours']
```

→ Prvi start ispravno kreira bazu i kompletnu šemu bez ijednog fajla iz dev
environment-a; proces ostaje živ (nema crash-a).

## Programatski smoke test (8 backlog koraka, offscreen)

Pokrenut sa `QT_QPA_PLATFORM=offscreen`, uz `sys._MEIPASS` usmjeren na stvarni
`_internal` folder bundle-a (testira `_MEIPASS` granu `resource_path()` protiv
stvarnog bundle layout-a):

```text
[resurs] logo OK: ...\dist\Dentaland\_internal\web\assets\logo.png
[resurs] doctor OK: ...\dist\Dentaland\_internal\desktop\assets\doctors\ljubo.png
[print] logo data URI OK (print preview bi prikazao logo)
[start] šema kreirana, doctor_id=1
[create] termin kreiran id=1
[scheduler] MainWindow otvoren (offscreen)
[reopen] termin potvrđen: Smoke Pacijent
SMOKE_RESULT: PASS (svih 8 koraka, simulirano offscreen)
```

## Šta je STVARNO testirano vs. šta ostaje za Radovana

Stvarno testirano (ista mašina, bez fizičke čiste mašine/VM-a):

- build je reproducibilan i ne zavisi od source checkout-a (exe pokrenut iz
  praznog foldera);
- prvi start kreira bazu u `DENTALAND_DATA_DIR` (user data folder ekvivalent);
- resursi (logo, fotografije doktora) su fizički u `_internal` i učitavaju se
  kroz `_MEIPASS` granu (QPixmap non-null);
- print logo se čita (data URI non-empty);
- perzistencija: kreiran termin → novi servis → termin potvrđen;
- MainWindow se konstruiše bez greške (offscreen).

NISAM potvrdio (ostaje za Radovana na drugoj/stvarnoj mašini):

- stvarno vizuelno prikazivanje GUI prozora i print preview dijaloga na
  ekranu (offscreen ne renderuje na ekran — ne tvrdim "clean machine
  potvrđeno");
- ponašanje pod stvarnim antivirusom/SmartScreen-om;
- rad sa stvarnim `%LOCALAPPDATA%\Dentaland` default putanjom (testirano sa
  `DENTALAND_DATA_DIR` override).

## Review

`PENDING` — implementer nije reviewer. Claude radi nezavisan MEDIUM-risk
review; Radovanov human approval obavezan prije merge-a.

## Integration status

`NOT_MERGED` — čeka nezavisan review.

## Handoff

CILJ: reproducibilan Windows build + dokaziv smoke test.

URAĐENO: `packaging/dentaland.spec`, `.ico`, pyproject dev deps, docs vodič,
README dopuna, stvarno izgrađen exe i stvarno pokrenut smoke ciklus (bundle +
programatski).

NE DIRATI: aplikacijski kod (`services/**`, `models.py`, `migrations/`,
`backend/`, `desktop/views/**`) — nijedan nije mijenjan.

SLJEDEĆE: Claude nezavisan review, pa Radovanov human approval (MEDIUM).
