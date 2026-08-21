---
task_id: DENT-IMPROVE-005
risk: MEDIUM
implementer: crush
reviewers: [claude]
verdict: PENDING
commits: []
created_at: 2026-08-21
---

# DENT-IMPROVE-005 — Minimalne Postavke

## Status

IMPLEMENTATION_COMPLETE / VERIFICATION_PENDING

## Šta je urađeno

- `src/dentaland/services/booking.py` — settings CRUD u `AppointmentService`:
  `list_doctors()` (svi + `aktivan`), `set_doctor_active()`, `add_service()`,
  `update_service()`, `list_working_hours()`, `set_working_hours()` (split
  shift + validacija: dan 1..7, od<do, bez preklapanja). `DoctorDTO.aktivan`
  i novi `WorkingHoursDTO`.
- `src/dentaland/services/__init__.py` — export `WorkingHoursDTO`.
- `desktop/views/settings_panel.py` (novo) — `SettingsPanel` (3 taba: Doktori
  checkbox, Usluge tabela + dodaj/uredi, Radno vrijeme po doktoru/danu +
  intervali), `changed` signal, duck-typed `store` (bez SQLAlchemy).
- `desktop/views/main_window.py` — ruta "postavke" sada vodi na
  `SettingsPanel` umjesto `StubPage`.
- Testovi: `tests/test_services.py` (+7), `tests/test_gui/test_settings_panel.py` (novo, +4).

## Probni signal (.agent/ validacija)

- Fajlova pročitano prije 1. izmjene: 6 (contract, `.agent/PROJECT_MAP.md`,
  `.agent/TASK_ROUTING.md`, `models.py`, `booking.py`, `main_window.py` +
  `blockout_panel.py` referenca).
- Koristio `.agent/`? DA — "Feature task"/"Desktop GUI task" + "Booking"
  paketi uputili direktno na `booking.py` + `desktop/views/` + GUI testove, bez `ls`/`find`.
- Pitao za pojašnjenje? NE.
- Ostao u allowed_paths? DA.

## Verifikacija

| Komanda | Rezultat |
|---|---|
| `pytest tests/ -q` | 251 passed |
| `ruff check src/dentaland desktop tests` | All checks passed |
| `mypy src/dentaland desktop backend` | Success (0 grešaka) |

## Review

PENDING — čeka nezavisan review (Claude).

## Integration status

NOT_MERGED — čeka review i human approval.
