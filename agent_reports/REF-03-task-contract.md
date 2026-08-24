---
task_id: REF-03
risk: MEDIUM
implementer: crush (podjela) + codex (F1 test fix, treća runda — Radovanova eksplicitna odluka)
reviewers: [pi (fresh reviewer 1), claude]
status: "DONE — MERGED u main (merge commit a02f31f, 2026-08-24), post-merge integration gate PASS (336 pytest, ruff, mypy)."
review_summary: >-
  booking.py (820 linija monolit) razbijen na appointments.py (novo),
  settings.py (novo), availability.py (prosireno REF-01), booking.py
  postaje tanak facade. F1 arhitektonski test (dokazuje da facade ne
  sadrzi poslovnu logiku) je prosao kroz tri runde Codex REJECT-a protiv
  Crush-a (string-match -> denylist -> jos rupa), pa je Radovan eksplicitno
  naredio da Codex sam zavrsi fix (allowlist + strog "tacno jedan poziv"
  AST oblik). Time Codex vise nije nezavisan Reviewer 1 za taj fix - Pi je
  preuzeo tu ulogu kao fresh reviewer, nezavisno ponovio sve mutacije + 5
  novih proba, sve hvataju. Claude (Reviewer 2): P6 nalaz (test odbija
  svaku privatnu metodu, ne samo data-access) ocijenjen kao namjerna,
  ispravna strogost, ne defekt.
created_at: 2026-08-24
merged_at: 2026-08-24
---

# REF-03 — Razbiti `booking.py` po servisnim odgovornostima

## Task Contract

**Cilj:** `booking.py` prestaje biti monolit. `AppointmentService` ostaje u
`booking.py` kao TANAK compatibility facade (ne premještati/preimenovati
fajl — GUI uvozi `from dentaland.services.booking import AppointmentService`),
a svaka javna metoda postaje jednoredna delegacija ka četiri fokusirana
modula.

**Risk:** MEDIUM (servisni sloj, dvostruki review za REF paket).

Izvor: `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`, sekcija 10.

Zavisnost: REF-01 (availability.py) + REF-02 (appointments_for_range) — oba
mergovana u main HEAD `f1b7acb` (potvrđeno `git log --oneline -1 main`).

## Tačan mapping (provjeren protiv trenutnog booking.py, 43 javne metode)

### `appointments.py` (novo) — Appointment CRUD/status/DTO + service lookup

```
AppointmentDTO, ServiceOptionDTO
create, update, get, all, all_combined, appointments_for_range,
mark_arrived, unmark_arrived, mark_confirmed, cancel, delete,
mark_completed, mark_no_show, awaiting_confirmation, cancelled_today, move
services, service_choices, service_options   (service READ za dropdown)
```

`all_combined()` MORA ostati identična (koristi je `print_schedule.py`, van
scope-a — ne diram taj fajl). `appointments_for_range()` mora zadržati
`selectinload` (REF-02, bez N+1) i intervalsku overlap semantiku.

### `availability.py` (proširiti postojeći, ne novi fajl) — dodati

```
CalendarBlockDTO, TimeOffDTO
time_off_for_week, breaks_for_week, create_time_off, list_time_off,
delete_time_off, _check_timeoff_overlap, _timeoff_dto
```

Overlap invariant (`validate_appointment_overlap`, `OverlapError`) je već tu
od REF-01 — ne diram tu logiku, samo dodajem pored nje.

### `settings.py` (novo) — doctor/service/working-hours administracija

```
DoctorDTO, WorkingHoursDTO
doctors, list_doctors, set_doctor_active,
add_service, update_service, list_working_hours, set_working_hours
ensure_seed_data, DEFAULT_DOCTORS, DEFAULT_SERVICES   (seed = settings domen)
```

### `requests.py` — nepromijenjen po logici

Facade `pending_requests`/`confirm_pending`/`reject_pending` već delegiraju
ka `requests.py` (koji koristi `availability.py`). Samo provjeriti da nisam
vratio overlap SQL duplikaciju.

### `booking.py` — tanak facade

`AppointmentService` ostaje klasa u `booking.py`. Re-eksportuje sve DTO-ove
(`AppointmentDTO`, `DoctorDTO`, `ServiceOptionDTO`, `CalendarBlockDTO`,
`TimeOffDTO`, `WorkingHoursDTO`), `OverlapError` i `ensure_seed_data`
(backward-compat import putanje koje testovi i GUI koriste). `from_sqlite`
ostaje facade (bootstrap + prvi doktor). `_require_doctor` ostaje facade
(vezan za `self.doctor_id` state).

## Tri nejasna slučaja — odluke (provjereno grep-om)

1. **`doctors()` vs `list_doctors()`** — NISU duplikati. `doctors()`
   (`booking.py:162`) vraća SAMO aktivne doktore (`DoctorDTO(id, ime)`),
   koriste ga scheduler/print (`day_view.py`, `week_view.py`,
   `print_schedule.py:171`, `main_window.py` dropdown). `list_doctors()`
   (`booking.py:602`) vraća SVE (aktivan+neaktivan, sa poljem `aktivan`),
   koristi ga SAMO `settings_panel.py:150`. Odluka: OBA idu u `settings.py`
   (doctor domen — `DoctorDTO` živi tamo po mapping-u; razdvajanje na dva
   modula bi stvorilo ciklični import jer `settings.py` vraća
   `ServiceOptionDTO` iz `appointments.py`). Obrazloženje ciklusa ispod.

2. **`list_working_hours()`** — READ operacija koju poziva SAMO
   `settings_panel.py:303` (grep potvrđen). Odluka: ide u `settings.py` uz
   `set_working_hours` (administracija radnog vremena). `WorkingHoursDTO`
   ide zajedno (jedino mjesto gdje se vraća).

3. **`service_choices` / `service_options` / `services`** — READ helperi za
   dropdown. `service_options()` → `main_window.py:636` (editor) i
   `settings_panel.py:190`; `service_choices()` → `requests_panel.py:32`;
   `services()` → `main_window.py:641` (FakeStore fallback) i test. Odluka:
   sva tri idu u `appointments.py` (service lookup za editor/request
   workflow; `ServiceOptionDTO` je tamo po mapping-u). `add_service`/
   `update_service` (CRUD) ostaju u `settings.py` — read i write iste tabele
   razdvojeni po SVRSI (plan sekcija 10: appointments = "service options za
   editor", settings = "services CRUD").

## Ciklični import — kako je riješen

Zavisnosti su jednosmjerne (bez ciklusa):

```text
availability.py → models.py
appointments.py → availability.py, models.py
settings.py     → appointments.py (ServiceOptionDTO), models.py
booking.py      → appointments.py, settings.py, availability.py, requests.py, models.py
```

`DoctorDTO` je u `settings.py` (po mapping-u), pa `doctors()` (koji vraća
`DoctorDTO`) mora biti u `settings.py` da `appointments.py` ne bi uvozio
`DoctorDTO` iz `settings.py` (što bi, uz `settings.py` → `appointments.py`
za `ServiceOptionDTO`, stvorilo ciklus). `breaks_for_week` (availability)
čita aktivne doktore direktno (`select(Doctor).where(aktivan)`), ne preko
`doctors()`, da ne bi povukao `settings.py` u `availability.py`.

## Acceptance

- [ ] appointment CRUD/status fizički nije pomiješan sa settings logikom (odvojeni fajlovi);
- [ ] request overlap ne duplira SQL (provjeriti da nije vraćena duplikacija);
- [ ] `tests/test_ref00_service_api_contract.py` prolazi NEPROMIJENJEN;
- [ ] `.agent/PROJECT_MAP.md` ažuriran (dodati appointments.py/settings.py/availability.py);
- [ ] full test suite prolazi.

## Allowed paths

```text
src/dentaland/services/booking.py
src/dentaland/services/appointments.py    (novo)
src/dentaland/services/availability.py    (prošireno)
src/dentaland/services/settings.py        (novo)
src/dentaland/services/__init__.py
tests/test_services.py
tests/test_ref03_booking_split.py         (novo)
.agent/PROJECT_MAP.md
agent_reports/**
```

## Forbidden paths

```text
desktop/**
src/dentaland/services/requests.py
src/dentaland/services/print_schedule.py
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

Baseline: **330 pytest passed** (izmjerio na svom worktree-u prije početka,
`13.61s`, 11 deprecation warnings iz zavisnosti).

## Review

Codex (test kvalitet, prvi) pa Claude (arhitektura). Radovan human approval
obavezan prije merge-a.

## Koordinacija

Worktree `Dentaland-worktrees/REF-03-booking-split`, grana
`task/REF-03-booking-split` (sa main-a `f1b7acb`). Claim prije početka.
