# Dentaland Project Map

Cilj ovog fajla: za manje od minute razumjeti gdje se šta nalazi, bez čitanja
implementacije. Detalje čitati tek kada konkretan task to zahtijeva — vidi
`TASK_ROUTING.md` za tačan read-set po tipu zadatka.

## Entry points

- `desktop/app.py` — PySide6 desktop entry point.
- `backend/main.py` — FastAPI lokalni backend / API entry point (javna forma).
- `web/index.html` + `web/app.js` — javna forma (frontend, bez build koraka).

## Domain model

- `src/dentaland/models.py` — SQLAlchemy modeli, glavna schema definicija.
- `migrations/` — Alembic istorija.
- `src/dentaland/backup.py` — backup logika.

Relevant tests: `tests/test_models.py`, `tests/test_backup.py`

## Booking domain

Od REF-03, `booking.py` je tanak compatibility facade (`AppointmentService`)
— ne drži poslovnu logiku, samo delegira ka fokusiranim modulima:

- `src/dentaland/services/booking.py` — facade `AppointmentService` (delegacija
  ka modulima ispod); backward-compat import putanja za GUI i štampu.
- `src/dentaland/services/appointments.py` — Appointment CRUD/status/DTO +
  `appointments_for_range` (range reads) + service lookup za editor.
- `src/dentaland/services/availability.py` — overlap invariant, TimeOff
  (blokada/odsustvo), kalendarski blokovi (odsustva + split-shift pauze).
- `src/dentaland/services/settings.py` — doktori/usluge/radno-vrijeme
  administracija (aktivacija doktora, CRUD usluga, radno vrijeme).

Relevant tests: `tests/test_services.py`, `tests/test_models.py`,
`tests/test_ref00_service_api_contract.py`, `tests/test_ref03_booking_split.py`

## Public requests (online zahtjevi)

- `src/dentaland/services/requests.py` — poslovna logika zahtjeva.
- `backend/main.py` — API za javnu formu.
- `desktop/views/requests_panel.py` — desktop panel za obradu zahtjeva.

Relevant tests: `tests/test_requests.py`, `tests/test_backend.py`,
`tests/test_gui/test_requests_panel.py`,
`tests/test_gui/test_process_request_dialog.py`

## Notifications

- `src/dentaland/services/notifications.py`

Relevant tests: `tests/test_notifications.py`

## Printing

- `src/dentaland/services/print_schedule.py` — priprema podataka za štampu.
- `desktop/print_document.py` — generisanje dokumenta.

Relevant tests: `tests/test_print_schedule.py`,
`tests/test_gui/test_print_document.py`

## Desktop scheduler (GUI)

Start here:
- `desktop/views/main_window.py`

Read only when relevant:
- `desktop/views/week_view.py` — nedjeljni prikaz rasporeda
- `desktop/views/day_view.py` — dnevni prikaz rasporeda
- `desktop/views/appointment_dialog.py` — dijalog za kreiranje novog termina
- `desktop/views/dialogs/` — dijalozi za akcije nad postojećim terminom:
  `appointment_details.py`, `appointment_editor.py`, `base_dialog.py`,
  `cancel_appointment.py`, `move_appointment.py`, `process_request.py`
- `desktop/views/sidebar.py` — bočna navigacija
- `desktop/views/stub_page.py` — placeholder ekrani za nedovršene sekcije
- `desktop/fake_data.py` — test/demo podaci za lokalni razvoj GUI-ja bez baze

GUI tests: `tests/test_gui/` (po fajlu: `test_app.py`, `test_main_window.py`,
`test_week_view.py`, `test_week_view_combined.py`, `test_day_view.py`,
`test_appointment_dialog.py`, `test_appointment_details_dialog.py`,
`test_destructive_dialogs.py`, `test_requests_panel.py`,
`test_process_request_dialog.py`, `test_print_document.py`)

Design/history docs (učitati SAMO ako task zavisi od dizajn odluke):
- `docs/istrazivanje-dentalni-scheduler-gui.md`
- `docs/redizajn/` (ako postoji relevantan materijal za tekući task)

## Web / javna forma

- `web/index.html`, `web/app.js`, `web/style.css`, `web/styles.css`
- `web/assets/` — slike, fontovi
- `web/tests/` — statični HTML test/preview fajlovi (`desktop.html`,
  `mobile.html`, `flow.html`, `privacy.html`) — ručna vizuelna provjera, ne
  pytest suite.

Spec: `docs/dentaland-javna-forma-spec.md` — učitati kad se dira UX/API
contract javne forme.

## Agent workflow (kako se radi na ovom projektu)

- `AGENTS.md`, `CLAUDE.md` — trajna pravila i navigacija (start here za svaki
  task).
- `docs/dentaland-agentski-razvoj.md` — kanonski detaljan procesni dokument
  (Task Contract, Reviewer Context Pack, structured verdict, risk-tier
  procedure).
- `agent_reports/` — istorija taskova, planovi, review-i, evidence.
- `agent_reports/README.md` — konvencija za pisanje reportova.
- `scripts/coordination.py` — claim/release/status/check koordinacija
  paralelnih agenata preko worktree-ova (vidi `AGENTS.md`).
- `.claude/settings.json` — Claude Code hook (auto `coordination.py
  hook-check` prije Edit/Write).
- `.codex/hooks.json` — ekvivalentna konfiguracija za Codex, status
  **UNVERIFIED** (nije potvrđeno da stvarno radi automatski — vidi
  `AGENTS.md`).

## Arhitektura / tehnički plan

- `docs/dentaland-razvojni-plan-v3.1.md` — tekući arhitektonski/tehnički
  izvor istine.
- `docs/dentaland-razvojni-plan.md` — raniji plan (provjeriti u
  v3.1-u da li je i dalje relevantan prije oslanjanja na stariju verziju).

## Run locally

- `README.md` — setup instrukcije.
- `scripts/dev_local.py` — lokalni dev runner.

## Baza

- SQLite lokalno (`dentaland.db` u root-u, gitignored za stvarne podatke).
- `alembic.ini` + `migrations/` za schema promjene.
