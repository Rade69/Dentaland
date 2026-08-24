---
task_id: REF-04
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: ASSIGNED — dodijeljeno Pi-ju (implementer)
created_at: 2026-08-24
---

# REF-04 — Uvesti pravi Controller sloj za appointment workflow

## Task Contract

**Napomena:** napisan naknadno (poslije implementacije) — procesna greška
implementera; sadržaj odražava plan i urađeno stanje.

**Cilj:** Izvući appointment workflow iz `MainWindow` u
`desktop/controllers/appointment_controller.py`.

**Risk:** MEDIUM (dira GUI sloj; dvostruki review za REF paket).

Izvor: `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`, sekcija 11.

Zavisnost: REF-03 — potvrđeno mergovan (main HEAD `3e3d11b`).

## Kritična nijansa (plan sekcija 3.2)

Controller SMIJE uvoziti PySide6 (QDialog) i pozivati Dialog klase kao crnu
kutiju (`.exec()`/`.get_data()`/`.show_error()`); NE smije crtati widgete niti
raditi SQL. Ovo NIJE isto pravilo kao "Service ne zna PySide6" — ne miješati.

## Šta uraditi

1. Novi `desktop/controllers/appointment_controller.py` sa metodama:
   `on_slot_selected`, `edit_appointment`, `open_appointment_details`,
   `handle_appointment_action` (dispatch + method_map za status akcije),
   `move_appointment`, `cancel_appointment`, `delete_appointment`,
   `service_options`. Retry-on-OverlapError `while True` obrazac se čuva 1:1.
2. `MainWindow` poslije taska: konstruiše views i Controller, povezuje
   signale na Controller, zadržava `_refresh_dashboard` (REF-05 posao) i
   high-level page navigation.
3. DI: `AppointmentController(store, parent_widget, refresh_callback)`.
   `parent_widget` je generički `QWidget` (ne importuje `MainWindow` klasu).
4. Late binding dijalog klasa (lazy import iz `main_window` modula) — da
   postojeći GUI testovi (monkeypatch na `main_window` modulu, i prije i
   poslije konstrukcije) ostanu nepromijenjeni.

## Acceptance

- MainWindow nema direktnu implementaciju appointment CRUD workflow-a;
- status akcije nisu implementirane u MainWindow;
- Controller ne importuje SQLAlchemy;
- View (dialog klase, day/week view) se ne mijenja;
- svi postojeći GUI testovi prolaze BEZ izmjene;
- `_refresh_dashboard` implementacija ostaje u MainWindow.

## Allowed paths

```text
desktop/controllers/appointment_controller.py   (novo)
desktop/controllers/__init__.py                 (novo)
desktop/views/main_window.py
tests/test_gui/test_appointment_controller.py   (novo)
agent_reports/**
```

## Forbidden paths

```text
desktop/views/dialogs/**
desktop/views/day_view.py
desktop/views/week_view.py
src/dentaland/services/**
backend/**
models.py
migrations/**
```

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Plus `tests/test_gui/test_main_window.py` PRIJE i POSLIJE (isti skup, bez
izmjene) — zabilježiti oba rezultata.

## Review

Codex (test kvalitet, prvi) pa Claude (arhitektura). Radovan human approval
obavezan prije merge-a.
