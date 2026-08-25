---
task_id: REF-08
risk: LOW
implementer: pi
reviewers: [codex, claude]
status: "IMPLEMENTED — čeka review. Bez commit-a (pravilo: nikad commit bez eksplicitnog zahtjeva)."
verification: "pytest 355 passed (baseline 355), ruff All checks passed, mypy no issues in 50 files, PyInstaller build + smoke PASS."
created_at: 2026-08-25
---

# REF-08 — Implementer izvještaj (Pi)

## Šta je urađeno

Posljednji cleanup prije finalnog arhitektonskog acceptance review-a (plan
sekcija 20): globalni QSS iz `main_window.py` u `desktop/presentation/theme.py`,
timezone konstanta u `src/dentaland/timezone.py` (6 produkcijskih mjesta
prestaju uvoziti iz `desktop.fake_data`), PyInstaller build potvrđen stvarnim
buildom + smoke testom, `.agent/PROJECT_MAP.md` ažuriran.

## Dio 1 — Theme/QSS

- Novi `desktop/presentation/theme.py` (peti fajl u presentation paketu).
- `GLOBAL_STYLESHEET: str` (175 linija QSS, module-level konstanta) +
  `apply_theme(window: QWidget) -> None` (postavlja QPalette na
  `QApplication.instance()` i `window.setStyleSheet(GLOBAL_STYLESHEET)`).
- `MainWindow._apply_style()` postala jednoredna delegacija `apply_theme(self)`.
- Iz `main_window.py` uklonjeni sada neiskorišteni importi `QColor`,
  `QPalette`, `QApplication` (ruff potvrđuje čisto).

**Obrazloženje oblika:** jedna ulazna tačka (`apply_theme`) drži paletu i QSS
zajedno, `GLOBAL_STYLESHEET` kao čista konstanta (testabilna bez Qt instanci),
`main_window.py` ne mora znati detalje palete.

**Behavior-preserving dokaz:** QSS u `GLOBAL_STYLESHEET` je byte-identičan
QSS-u koji je bio u `main_window.py:_apply_style()` — upoređeno programatski
(`git show HEAD:...` vs `theme.py`, poslije `textwrap.dedent`):
`orig 175 lines == new 175 lines`, `EQUAL (byte-identical): True`.

## Dio 2 — Timezone (tačan mapping)

Novi `src/dentaland/timezone.py`: `SARAJEVO = ZoneInfo("Europe/Sarajevo")`
(jedina definicija).

Zamijenjenih 6 uvoza `from desktop.fake_data import SARAJEVO` →
`from dentaland.timezone import SARAJEVO`:

| # | Fajl | Linija |
|---|---|---|
| 1 | desktop/controllers/schedule_controller.py | 25 |
| 2 | desktop/views/blockout_panel.py | 26 |
| 3 | desktop/views/day_view.py | 33 |
| 4 | desktop/views/dialogs/blockout_delete_confirm.py | 15 |
| 5 | desktop/views/main_window.py | 37 |
| 6 | desktop/views/week_view.py | 32 |

`desktop/fake_data.py` sada importuje `SARAJEVO` iz `dentaland.timezone`
(uklonjena lokalna definicija + `from zoneinfo import ZoneInfo`).

Grep potvrda poslije izmjene: `from desktop.fake_data import` → **0** pojavljivanja
u `desktop/` i `src/`.

## Dio 3 — PyInstaller build (stvaran build, ne pretpostavka)

```text
$ python -m PyInstaller packaging/dentaland.spec --noconfirm
INFO: Build complete! The results are available in: .../dist
```

- `dist/Dentaland/Dentaland.exe` + `_internal/` generisani.
- Warn fajl (`build/dentaland/warn-dentaland.txt`): **nema** "missing module"
  za `dentaland.timezone`, `desktop.presentation.theme` ni `desktop.presentation`
  — PyInstaller ih je automatski pokupio preko statičkih importa
  (`pathex=[ROOT, ROOT/src]`); **spec fajl NIJE trebao izmjenu**.
- Smoke test (obrazac DENT-IMPROVE-009): exe pokrenut iz PRAZNOG foldera van
  repoa, bez `PYTHONPATH`, `QT_QPA_PLATFORM=offscreen`,
  `DENTALAND_DATA_DIR` na scratch:

```text
run_dir:  C:\Users\...\Temp\ref08-run-ijzk6779
data_dir: C:\Users\...\Temp\ref08-data-4ltgbitm
process alive after 12s: True (returncode=None)
db files in data_dir: ['dentaland.db']
db size: 24576
tables: ['appointments', 'doctors', 'services', 'time_off', 'working_hours']
```

→ ImportError nema (import lanac `app.py → main_window → theme/timezone`
prolazi), prvi start kreira punu šemu.

## Dio 4 — MainWindow cilj

Provjereno: `main_window.py` nakon REF-04..08 sadrži window construction,
sidebar/page registration, high-level routing, controller construction/wiring,
window-level lifecycle. Nema OČIGLEDNOG propuštenog posla osim theme/timezone
(koji su urađeni). Poznati tehnički dug (3 mjesta "gledanja nazad" iz
REF-04/05, `WeekView._DOCTOR_PALETTE` iz REF-06) je već dokumentovan kao
namjeran kompromis — nije novi nalaz, ne diram.

## Dio 5 — .agent/PROJECT_MAP.md

Ažurirano: `src/dentaland/timezone.py` (Domain model), `desktop/controllers/`
(4 kontrolera) + `desktop/presentation/` (3 modula) u Desktop scheduler
sekciji, GUI test lista dopunjena stvarnim fajlovima.

## OUT_OF_SCOPE_FINDING (prijavljeno, ne dirano)

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  SARAJEVO = ZoneInfo("Europe/Sarajevo") je NEZAVISNO REDEFINISANA (ne
  uvezena — doslovno ista linija kopirana) na 9 dodatnih mjesta. Ovo je
  veći problem od onoga što plan opisuje (redundancija, ne samo pogrešan
  izvor), ali konsolidacija svih 9 bi dramatično proširila scope LOW taska
  (servisni sloj + svi dialozi).
locations:
  - src/dentaland/services/notifications.py:40
  - src/dentaland/services/print_schedule.py:27
  - desktop/views/dialogs/appointment_details.py:21
  - desktop/views/dialogs/appointment_editor.py:32
  - desktop/views/dialogs/cancel_appointment.py:17
  - desktop/views/dialogs/delete_appointment.py:23
  - desktop/views/dialogs/move_appointment.py:27
  - desktop/views/dialogs/process_request.py:20
  - desktop/views/requests_page.py:23
risk: LOW
proposed_task: REF-09 ili poseban cleanup — konsolidovati preostalih 9
  nezavisnih SARAJEVO definicija u dentaland.timezone.
```

## Verifikacija (doslovni rezultati)

```text
$ python -m pytest tests/ -q
355 passed, 11 warnings in 15.96s        (baseline prije koda: 355 passed)

$ python -m ruff check src/dentaland desktop backend tests
All checks passed!

$ python -m mypy src/dentaland desktop backend
Success: no issues found in 50 source files
```

## Acceptance

- [x] globalni theme više nije ugrađen u MainWindow workflow kod (QSS/paleta
  u `theme.py`, `_apply_style` = 1 linija);
- [x] production view (6 mjesta) ne zavisi od fake_data za timezone (grep 0);
- [x] PyInstaller build i dalje radi — dokazano stvarnim buildom + smoke testom;
- [x] `.agent/PROJECT_MAP.md` opisuje stvarno stanje;
- [x] preostalih 9 SARAJEVO redefinicija prijavljeno kao OUT_OF_SCOPE_FINDING,
  ne dirano.

## Nije urađeno / namjerno izostavljeno

- Nema commit-a — po pravilu, čekam eksplicitan zahtjev.
- 9 nezavisnih SARAJEVO redefinicija nisu dirane (OUT_OF_SCOPE).
- `desktop/views/dialogs/appointment_details.py` itd. (forbidden_paths) nisu
  dirani.
- `packaging/dentaland.spec` nije mijenjan (nije trebao).
