---
task_id: REF-04
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-24
---

# REF-04 — Uvesti pravi Controller sloj za appointment workflow

## Task Contract

Izvor: `agent_reports/REF-04-task-contract.md` (napisan PRIJE koda). Zavisnost
REF-03 potvrđena (main HEAD `3e3d11b`, granano sa njega). MEDIUM risk, dva
reviewera.

## Mapping (MainWindow → AppointmentController)

| MainWindow (prije) | AppointmentController (poslije) |
|---|---|
| `_on_slot_selected(start)` | `on_slot_selected(start)` — new appointment + retry-on-OverlapError petlja |
| `_edit_appointment(appt)` | `edit_appointment(appt)` — isti retry obrazac |
| `_open_appointment_details(appt_id)` | `open_appointment_details(appt_id)` — delegira na `handle_appointment_action` |
| `_handle_appointment_action(appt_id, action)` | `handle_appointment_action(appt_id, action)` — dispatch + method_map + ValueError→QMessageBox |
| `_move_appointment(appt)` | `move_appointment(appt)` |
| `_cancel_appointment(appt)` | `cancel_appointment(appt)` |
| `_delete_appointment(appt)` | `delete_appointment(appt)` |
| `_service_options()` | `service_options()` |

Retry-on-OverlapError `while True: dialog.exec()...` obrazac je prenesen
1:1 (suptilna UX logika očuvana).

## Ključne odluke (i zašto)

1. **Late binding dijalog klasa** — Controller dohvata dijaloge lazy importom
   iz `desktop.views.main_window` u trenutku poziva, umjesto module-level
   importa. Razlog: postojeći GUI testovi monkeypatch-uju dijaloge na
   `desktop.views.main_window` modulu, a neki to rade i NAKON konstrukcije
   `MainWindow`-a (`test_delete_akcija_*`, `test_cancel_na_terminalnom_*`).
   DI kroz konstruktor (early binding) je prvo isproban i odbijen jer je
   "zamrzavao" pravu klasu i rušio te testove (blokirao na `dialog.exec()`).
2. **`main_window` re-eksportuje dijaloge + `OverlapError`** (`# noqa: F401`)
   — isključivo radi late bindinga i postojećih testova; implementacija
   workflow-a NE živi u `main_window`.
3. **Tri tanke delegacije u `MainWindow`** (`_handle_appointment_action`,
   `_cancel_appointment`, `_delete_appointment`) — zadržane jer postojeći
   testovi pozivaju te privatne metode direktno (`win._handle_appointment_action(...)`).
   To je passthrough na Controller, ne implementacija.

## DI

`AppointmentController(store, parent_widget, refresh_callback)`. Store je
generički `Any` (isti obrazac kao MainWindow), parent je generički `QWidget`
(Controller ne importuje `MainWindow` klasu). UI kontekst (`_doctors`,
`_has_doctors`, `_current_doctor_id`) se čita kroz `getattr` na generičkom
parent-u.

## Changed files

- `desktop/controllers/__init__.py` — novi paket.
- `desktop/controllers/appointment_controller.py` — novi Controller.
- `desktop/views/main_window.py` — workflow metode uklonjene; wiring na
  Controller; 3 tanke delegacije; re-eksporti (dijalozi + OverlapError).
- `tests/test_gui/test_appointment_controller.py` — 5 novih testova.

`desktop/views/dialogs/**`, `desktop/views/day_view.py`,
`desktop/views/week_view.py`, `src/dentaland/services/**`, `backend/**`,
`models.py`, `migrations/**` — NIJEDAN nije diran.

## Verifikacija (rezultati)

```text
pytest tests/ -q
→ 341 passed, 11 warnings   (336 baseline + 5 novih Controller testova)

ruff check src/dentaland desktop backend tests
→ All checks passed!, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 42 source files
```

### test_main_window.py — PRIJE i POSLIJE (dokaz safety net-a)

```text
PRIJE  (main_window na HEAD 3e3d11b): 32 passed in 5.07s
POSLIJE (sa Controller-om):            32 passed in 5.48s
```

Isti skup od 32 testa prolazi i prije i poslije — nijedan GUI test nije
mijenjan.

## Acceptance

- [x] MainWindow nema direktnu implementaciju appointment CRUD workflow-a
      (metode premještene u Controller; ostale 3 delegacije su passthrough);
- [x] status akcije više nisu implementirane u MainWindow (`method_map` je u
      Controller-u);
- [x] Controller ne importuje SQLAlchemy (grep: NEMA `sqlalchemy` u fajlu);
- [x] View (dialog klase, day/week view) nije mijenjan — samo drugačije
      povezan;
- [x] svi postojeći GUI testovi prolaze bez izmjene (32/32 prije i poslije);
- [x] `_refresh_dashboard` implementacija ostaje u MainWindow (nije dirana,
      REF-05 posao).

## Review

`PENDING` — Codex (test kvalitet, prvi), pa Claude (arhitektura). Radovan
human approval obavezan prije merge-a.

## Integration status

`NOT_MERGED` — čeka dva review-a.

## Handoff

CILJ: appointment workflow izvučen iz MainWindow u Controller, bez UX
promjene.

URAĐENO: `AppointmentController` (on_slot_selected/edit/details/action/
move/cancel/delete/service_options), MainWindow wiring + re-eksporti + 3
delegacije, 5 testova, PRIJE/POSLIJE dokaz.

NE DIRATI: dialogs, day_view, week_view, services, backend, models,
migrations.

SLJEDEĆE: Codex review → Claude review → Radovan human approval → merge.
