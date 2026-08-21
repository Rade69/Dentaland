# DENT-IMPROVE-005 — Plan (MEDIUM)

**Cilj:** Minimalne postavke — doktori (lista, aktivan/neaktivan), usluge
(naziv, trajanje, buffer, dodavanje/uređivanje), radno vrijeme (doktor, dan,
split-shift intervali). Zamijeniti seed-zavisnost stvarnim CRUD-om.

**Pogođeno:**
- `src/dentaland/services/booking.py` — settings CRUD metode u `AppointmentService`.
- `src/dentaland/services/__init__.py` — export novih DTO.
- `desktop/views/settings_panel.py` (novo) — `SettingsPanel`.
- `desktop/views/main_window.py` — wire umjesto `StubPage("Postavke")`.
- `tests/test_services.py`, `tests/test_gui/test_settings_panel.py` (novo).

**Servisne metode (u AppointmentService):**
- `list_doctors() -> list[DoctorDTO]` — svi (aktivan+neaktivan); `DoctorDTO`
  dobija `aktivan: bool = True`.
- `set_doctor_active(doctor_id, active) -> DoctorDTO` — ne briše istoriju.
- `list_services() -> list[ServiceOptionDTO]` (re-export postojećeg
  `service_options()`).
- `add_service(naziv, trajanje_min, buffer_min)` / `update_service(...)` —
  validacija: trajanje>0, buffer>=0, naziv ne-prazan.
- `list_working_hours(doctor_id) -> list[WorkingHoursDTO]`.
- `set_working_hours(doctor_id, dan_u_sedmici, intervals)` — split shift;
  validacija: od<do, intervali se ne preklapaju; zamjena (obriši+upiši).

**GUI (`SettingsPanel`):** tri sekcije (doktori checkbox, usluge lista +
dodaj/uredi, radno vrijeme po doktoru/danu + intervali), `changed` signal,
isti obrazac kao `BlockoutPanel` (duck-typed `store`, bez SQLAlchemy).

**Šta NE dirati:** `models.py`, `migrations/`, `backend/`, `web/`,
`desktop/views/sidebar.py`, ostali dialogs.

**Verifikacija:** service tests + GUI tests + `pytest tests/ -q`,
`ruff check`, `mypy src/dentaland desktop backend` (baseline).

**Probni signal (zapisujem prije 1. izmjene):**
- Fajlova pročitano prije 1. izmjene: 6 (contract, `.agent/PROJECT_MAP.md`,
  `.agent/TASK_ROUTING.md`, `models.py`, `booking.py`, `main_window.py` +
  `blockout_panel.py` kao referenca).
- Koristio `.agent/`? DA — "Feature task"/"Desktop GUI task" + "Booking"
  paketi uputili na `booking.py` + `desktop/views/` + GUI testove, bez `ls`.
- Pitao za pojašnjenje? NE.
- Ostao u allowed_paths? DA (claim paths gore).

**Rollback:** izolovano u worktree/grani `task/DENT-IMPROVE-005-settings`;
`main` netaknut do merge-a.
