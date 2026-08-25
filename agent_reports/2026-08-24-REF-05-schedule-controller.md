---
task_id: REF-05
risk: MEDIUM
implementer: crush
reviewers: [codex, claude]
status: "READY FOR REVIEW — worktree REF-05-schedule-controller, grana task/REF-05-schedule-controller (sa main-a daf3074)."
created_at: 2026-08-24
---

# REF-05 — ScheduleController + refresh orchestration (implementer izvještaj)

## Šta je urađeno

`MainWindow` više ne koordinira Day/Week state, doctor filter, schedule
refresh, status summary ni doctor counts. Uveden je `ScheduleController`
(`desktop/controllers/schedule_controller.py`), a `WeekView`/`DayView` su
prestali sami fetch-ovati — dobijaju dataset kroz novu metodu
`render_schedule(appointments, blocks)` i računaju counts iz tog istog
cache-a.

Napomena o imenu: plan predlaže `render(appointments, blocks)`, ali
`QWidget` već ima metodu `render(QPainter, ...)` — preklapanje bi dalo
`mypy` grešku `[override]` i shadow-ovalo Qt-ovu metodu. Zato je nova metoda
nazvana `render_schedule` (funkcionalno identično).

## PRIJE / POSLIJE — broj fetch poziva (dokaz, ne tvrdnja)

### PRIJE (stari `_refresh_dashboard`, čitanjem starog koda)

`_refresh_dashboard()` je za AKTIVAN WeekView pozivao:

```text
week_view.refresh()                 → appointments_for_range #1  + time_off + breaks
day_view.refresh()                  → appointments_for_range #2  + time_off + breaks  (SKRIVENI view)
_update_status_legend()             → visible_status_counts → appointments_for_range #3
_update_doctor_panel_counts()       → visible_doctor_counts → appointments_for_range #4
```

Dakle **4× `appointments_for_range` + 2× (time_off + breaks)** po jednom
refresh ciklusu, uključujući fetch skrivenog view-a.

### POSLIJE (novi `ScheduleController.refresh`, deterministički test)

```text
ScheduleController.refresh()
  → _fetch_appointments()  → appointments_for_range #1
  → _fetch_blocks()        → time_off_for_week #1 + breaks_for_week #1
  → active_view.render_schedule(...)      (samo AKTIVAN view)
  → visible_status_counts() / visible_doctor_counts()  (iz cache-a, 0 fetch-a)
```

Dakle **1× `appointments_for_range` + 1× time_off + 1× breaks** po refresh
ciklusu. Skriveni view se ne renderuje ni ne fetch-uje.

Dokaz: `tests/test_gui/test_schedule_controller.py` — query-counter fake
store, 6 testova (vidi "Testovi" ispod). Stvaran output:

```text
$ python -m pytest tests/test_gui/test_schedule_controller.py -q
6 passed in 0.05s
```

Ključne asertacije: `appointments_for_range_calls == 1`,
`time_off_for_week_calls == 1`, `breaks_for_week_calls == 1`,
`week_view.render_calls == 1`, `day_view.render_calls == 0` (skriveni).

## Arhitektonska podjela

- **`ScheduleController`** (novo) — drži `week_start`/`current_day`/
  `_current_doctor_id`, radi jedan snapshot po refresh-u, poziva
  `render_schedule` na aktivnom view-u, i šalje counts kroz callback-ove
  (`on_status_counts`/`on_doctor_counts`/`on_range_label`). Čita
  `view_stack.currentWidget()` samo da odredi aktivan view; ne crta widgete
  ni ne radi SQL (plan sekcija 3.2).
- **`WeekView`/`DayView`** — uklonjeni `_fetch_appointments`/`_fetch_blocks`;
  dodati cache `_appointments`/`_blocks` i `render_schedule()`. `refresh()`
  je sada interni re-draw iz cache-a (bez fetch-a). `visible_status_counts`/
  `visible_doctor_counts` računaju iz cache-a. `DayView` dodatno filtrira
  "počinje u danu" kroz `_day_appointments()`/`_day_blocks()` (presentation,
  ne fetch).
- **`MainWindow`** — `_move_week`/`_go_today`/`_show_day_view`/
  `_show_week_view`/`_on_tab_changed` su tanke delegacije ka controller-u;
  `_refresh_dashboard()` i dalje refreshuje dashboard panels + requests
  page + sidebar pending count (NISU scheduler), a scheduler refresh ide kroz
  `ScheduleController.refresh()`. Auto-refresh (20s) poziva isti
  `_refresh_dashboard()` — sidebar pending count ostaje ažuran, skriveni
  scheduler view se ne fetch-uje.
- **`MainWindow.week_start`** — zadržan kao read-only `@property` koji
  delegira `self._schedule_controller.week_start`, radi backward-compat
  (`test_main_window.py` ga čita; print metode ga koriste).

## Izmjene GUI testova (obrazloženje)

View više ne fetch-uje sam — testovi koji su mock-ovali store i očekivali
fetch u `__init__`/`refresh()` sada moraju eksplicitno render-ovati. Izmjena
je mehanička i mijenja KAKO view dobija podatke, ne ŠTA prikazuje (GUI prikaz
identičan). U svakom test fajlu dodat je helper koji fetch-uje iz store-a i
render-uje, pa su pozivi `refresh()`/konstrukcije zamijenjeni njime.

- **`tests/test_gui/test_week_view.py`** (12 testova): dodat `_snapshot`/
  `_render_week`; `week_view.refresh()` → `_render_week(week_view, store)`.
  `test_prevlacenje_termina_azurira_vrijeme` dodatno render-uje POSLIJE
  `move` (jer `move_appointment_to_slot` više ne re-draw-uje interno — sada
  emituje `appointment_moved`, a controller refreshuje; test nema controller).
  `test_blockout_je_spojen...` i `test_visible_doctor_counts...` render-uju
  eksplicitno.
- **`tests/test_gui/test_day_view.py`** (13 konstrukcija): dodat `_render_day`;
  `view = DayView(...)` + `_render_day(view, appointment_service, DAY)`.
- **`tests/test_gui/test_week_view_combined.py`** (5 testova, dodat u obim O1):
  dodat `_snapshot`/`_render_week`; fixture i `test_termin_od_60_min...`
  render-uju eksplicitno.
- **`tests/test_gui/test_main_window.py`** — NIJE mijenjan; `week_start`
  property omogućava da `test_navigacija_mijenja_sedmicu_i_sidebar_rutu`
  i dalje prolazi nepromijenjen.
- **`tests/test_gui/test_schedule_controller.py`** (novo, 6 testova) — query-
  counter dokaz broja fetch poziva + aktivan-view + counts-iz-istog-dataseta.

## Kalendarski blokovi

`calendar_blocks_for_range` iz plana NE postoji — koristim postojeće
`time_off_for_week`/`breaks_for_week` (week-based). Controller ih poziva
JEDNOM po refresh-u; `DayView` interno filtrira blokove na svoj dan. Nisam
dodao novu servisnu funkciju (servisni sloj nedirnut).

## Snapshot

Obična torka/dict — controller fetch-uje i prosleđuje `(appointments,
blocks)` kroz `render_schedule`; nema formalnog dataclass-a (plan dozvoljava).

## Verifikacija (stvaran output)

```text
$ python -m pytest tests/ -q
347 passed, 11 warnings in 10.42s

$ ruff check src/dentaland desktop backend tests
All checks passed!

$ mypy src/dentaland desktop backend
Success: no issues found in 43 source files
```

Baseline prije početka: 341 passed. Sada 347 (341 + 6 novih testova).
`test_ref00_service_api_contract.py` i servisni sloj netaknuti.

## Dirnuti fajlovi

```text
M  desktop/views/day_view.py
M  desktop/views/main_window.py
M  desktop/views/week_view.py
M  tests/test_gui/test_day_view.py
M  tests/test_gui/test_week_view.py
M  tests/test_gui/test_week_view_combined.py
A  desktop/controllers/schedule_controller.py
A  tests/test_gui/test_schedule_controller.py
A  agent_reports/REF-05-task-contract.md
```

`desktop/controllers/__init__.py` nije trebao izmjenu (importi idu direktno).
`desktop/controllers/appointment_controller.py`, `dialogs/**`, `services/**`,
`backend/**`, `models.py`, `migrations/**` — sve nedirano (forbidden paths).

## Out of scope / napomene

- Drag&drop `move_appointment_to_slot` i dalje radi `store.move` direktno u
  view-u (postojeći obrazac), ali sada emituje `appointment_moved` umjesto
  internog re-draw-a; `MainWindow` povezuje taj signal na
  `ScheduleController.refresh()`. Prelazak drag&drop-a na `AppointmentController`
  je van scope-a ovog taska (nije ni bio u REF-04 scope-u).
- `MainWindow._current_doctor_id` je zadržan kao atribut jer ga
  `AppointmentController` čita kroz `getattr` (REF-04 tehnički dug,
  dokumentovan u CURRENT_STATE). `ScheduleController` drži svoju kopiju za
  schedule state.
