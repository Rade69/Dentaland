---
task_id: REF-03
risk: MEDIUM
implementer: crush
reviewers: [codex, claude]
status: "READY FOR REVIEW — worktree REF-03-booking-split, grana task/REF-03-booking-split (sa main-a f1b7acb)."
created_at: 2026-08-24
---

# REF-03 — Razbiti `booking.py` po servisnim odgovornostima (implementer izvještaj)

## Šta je urađeno

`booking.py` (820 linija monolit) je razbijen na tanak facade + tri fokusirana
modula. `AppointmentService` je ostao u `booking.py` kao klasa (bez
preimenovanja/premještanja fajla — GUI import `from dentaland.services.booking
import AppointmentService` i dalje radi). Svaka javna metoda je jednoredna
delegacija ka odgovarajućem modulu.

## Tačan mapping (43 javne metode → gdje otišla)

### `src/dentaland/services/appointments.py` (novo, 405 linija)

Appointment CRUD/status/DTO + service lookup:

```text
AppointmentDTO, ServiceOptionDTO
create_appointment, update_appointment, get_appointment, list_appointments (all),
all_combined_appointments (all_combined), appointments_for_range,
mark_arrived, unmark_arrived, mark_confirmed, cancel_appointment,
delete_appointment, mark_completed, mark_no_show,
awaiting_confirmation, cancelled_today, move_appointment,
list_service_names (services), service_choices, service_options
```

- `all_combined_appointments` je bukvalna kopija ranijeg `all_combined()`
  (isti lazy obrazac, BEZ eager load — namjerno, jer je koristi
  `print_schedule.py` koji nije diran).
- `appointments_for_range` zadržava `selectinload` (REF-02, bez N+1) i
  intervalsku overlap semantiku `start < range_end AND end > range_start`.

### `src/dentaland/services/availability.py` (prošireno, 54 → 245 linija)

Dodato (pored netaknutog `validate_appointment_overlap`/`OverlapError`):

```text
CalendarBlockDTO, TimeOffDTO
time_off_for_week, breaks_for_week, create_time_off, list_time_off,
delete_time_off, _check_timeoff_overlap, _timeoff_dto
```

`breaks_for_week` čita aktivne doktore DIREKTNO (`select(Doctor).where(aktivan)`)
umjesto kroz `doctors()` — da ne povuče `settings.py` u `availability.py`
(vidi "Ciklični import" ispod).

### `src/dentaland/services/settings.py` (novo, 219 linija)

Doctor/Service/WorkingHours administracija + seed:

```text
DoctorDTO, WorkingHoursDTO
doctors, list_doctors, set_doctor_active,
add_service, update_service, list_working_hours, set_working_hours
ensure_seed_data, DEFAULT_DOCTORS, DEFAULT_SERVICES
```

### `src/dentaland/services/booking.py` (820 → ~245 linija, facade)

`AppointmentService` + `from_sqlite` + `set_doctor` + `_require_doctor` + sve
javne metode kao delegacije. Re-eksportuje sve DTO-ove, `OverlapError` i
`ensure_seed_data` (backward-compat import putanje).

### `src/dentaland/services/requests.py` — nedirano

Facade `pending_requests`/`confirm_pending`/`reject_pending` već su delegirale
ka `requests.py`; nisam vratio overlap SQL duplikaciju (provjereno —
`requests.py` i dalje koristi `validate_appointment_overlap`).

## Tri nejasna slučaja — odluke i obrazloženje

1. **`doctors()` (aktivni) vs `list_doctors()` (svi)** — NISU duplikati.
   `doctors()` vraća SAMO aktivne (`where(aktivan.is_(True))`, `DoctorDTO(id,
   ime)`), koriste ga scheduler/print (`day_view.py`, `week_view.py`,
   `print_schedule.py:171`, `main_window.py` dropdown). `list_doctors()` vraća
   SVE sa poljem `aktivan`, koristi ga SAMO `settings_panel.py:150`. Odluka:
   OBA idu u `settings.py` (doctor domen, `DoctorDTO` je tamo po mapping-u).
   Razlog zašto `doctors()` nije u `appointments.py`: `settings.py` vraća
   `ServiceOptionDTO` (koji je po mapping-u u `appointments.py`), pa bi
   `appointments.py` → `settings.py` (za DoctorDTO) + `settings.py` →
   `appointments.py` (za ServiceOptionDTO) stvorio ciklični import. Jednosmjerna
   zavisnost `settings.py` → `appointments.py` to razrješava.

2. **`list_working_hours()`** — READ, poziva ga SAMO `settings_panel.py:303`
   (grep potvrđen). Odluka: `settings.py` uz `set_working_hours`
   (administracija radnog vremena); `WorkingHoursDTO` ide zajedno (jedino
   mjesto gdje se vraća).

3. **`services()` / `service_choices()` / `service_options()`** — READ helperi
   za dropdown. `service_options()` → `main_window.py:636` + `settings_panel.py:190`;
   `service_choices()` → `requests_panel.py:32`; `services()` →
   `main_window.py:641` (FakeStore fallback). Odluka: sva tri u `appointments.py`
   (service lookup za editor/request workflow; `ServiceOptionDTO` je tamo po
   mapping-u). `add_service`/`update_service` (CRUD) ostaju u `settings.py` —
   read i write iste tabele razdvojeni po SVRSI (plan sekcija 10).

## Ciklični import — kako je riješen

Zavisnosti su strogo jednosmjerne:

```text
availability.py → models.py
appointments.py → availability.py, models.py
settings.py     → appointments.py (ServiceOptionDTO), models.py
booking.py      → appointments.py, settings.py, availability.py, requests.py, models.py
```

`DoctorDTO` je u `settings.py` (mapping), pa `doctors()` (vraća `DoctorDTO`)
mora biti u `settings.py` — inače bi `appointments.py` uvozio `DoctorDTO` iz
`settings.py`, a `settings.py` već uvozi `ServiceOptionDTO` iz `appointments.py`
= ciklus.

## Verifikacija (stvaran output, doslovno)

```text
# Prije početka (baseline na worktree-u, main f1b7acb):
330 passed, 11 warnings in 13.61s

# Poslije refaktora + 6 novih arhitektonskih testova:
336 passed, 11 warnings in 10.77s

# tests/test_ref00_service_api_contract.py (safety net) — NEPROMIJENJEN, prolazi:
24 passed (test_ref00_service_api_contract + test_ref00_overlap_error_contract + test_availability)

# ruff check src/dentaland desktop backend tests:
All checks passed!

# mypy src/dentaland desktop backend:
Success: no issues found in 40 source files
```

`tests/test_ref00_service_api_contract.py` je prošao **nepromijenjen** — nije
slomljen facade compatibility (imena metoda, DTO polja, `services.__all__` set).

## Dirnuti fajlovi

```text
M  .agent/PROJECT_MAP.md                 (dodana appointments/settings/availability)
M  src/dentaland/services/availability.py (prošireno, 54 → 245)
M  src/dentaland/services/booking.py      (monolit → facade, 820 → ~245)
A  src/dentaland/services/appointments.py (novo, 405)
A  src/dentaland/services/settings.py     (novo, 219)
A  tests/test_ref03_booking_split.py      (novo, 6 arhitektonskih testova)
A  agent_reports/REF-03-task-contract.md
```

`src/dentaland/services/__init__.py` NIJE mijenjan — `booking.py` i dalje
re-eksportuje isti skup simbola, pa `services.__all__` ostaje identičan.

Broj dirnutih fajlova (6 + 2 reporta) je u okviru plana — nije došlo do
neočekivanog širenja obima (plan sekcija 22 kill/rollback pravilo nije
trigerovano).

## Out of scope / napomene

- `print_schedule.py`, `requests.py`, `desktop/**`, `models.py`, `migrations/**`
  — sve nedirano (forbidden paths poštovan).
- `__init__.py` nije trebao promjenu (re-eksport kroz facade je dovoljan).
