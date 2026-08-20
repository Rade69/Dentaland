# Review — DENT-DESKTOP-F (hard delete termina, HIGH)

Reviewer 1: Crush | Implementer: Claude | Risk: HIGH | Datum: 2026-08-19

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
data-safety: PASS
blocking_findings: []
```

## Prozna analiza

### 1. FK/cascade — nezavisno provjereno (ne na riječ implementera)

`src/dentaland/models.py` pregledan samostalno. Sve tabele: `doctors`,
`services`, `working_hours`, `time_off`, `appointments`. Svi `ForeignKey`
upiti idu **KA** `doctors.id` i `services.id` — `Appointment` je isključivo
"dijete" (`doctor_id`, `service_id`). `grep "appointments.id"` → prazno;
nijedna tabela ne referencira `appointments.id`. Prost `session.delete(appt)`
nema cascade posljedica. Potvrđeno i runtime testom
`test_delete_ne_dira_druge_termine` (dva termina, obrisan jedan, drugi
netaknut).

### 2. `AppointmentService.delete()` (booking.py)

`get → None-check → ValueError → session.delete → commit`, bez status-provjere.
Tačno po acceptance: radi za bilo koji status, nepostojeći ID baca
`ValueError("...nije pronađen")`. Nema dodira sa `cancel()`/`mark_*` logikom.

### 3. Enter-safety (F.4)

`DeleteAppointmentDialog`-ovo dugme eksplicitno `setAutoDefault(False)` +
`setDefault(False)` — potvrđeno u kodu i testom
`test_delete_dugme_ne_reaguje_na_enter` (`autoDefault() is False`,
`isDefault() is False`). Ispravno odstupanje od `BaseDialog.add_primary_button`
default-a, dokumentovano.

### 4. "Dostupno za sve statuse" — svuda ispravno

- `_status_key()`: `CANCELLED`/`NO_SHOW` → `"cancelled"`, `COMPLETED` →
  `"completed"`, pa je `terminal = status_key in {"completed","cancelled"}`
  tačan (pokriva sva tri terminalna statusa).
- Detalji (`appointment_details.py`): dugme "Izbriši termin" dodano **van**
  `if not terminal:` bloka, direktno u `body_layout` (iza `addSpacing(6)`),
  pa je uvijek vidljivo — za terminalne termine je jedina akcija.
- Oba context menija (`week_view.py`, `day_view.py`): `menu.addSeparator()` +
  "Izbriši termin" dodani **van** uslovnog bloka, na dnu, uvijek prisutni.

### 5. Scope

`git diff --name-only` (plan..HEAD) → 15 fajlova, svi u `allowed_paths`.
`models.py`, `migrations/`, `base_dialog.py`, `appointment_editor.py`,
`move_appointment.py`, `cancel_appointment.py`, `process_request.py`,
`requests_panel.py`, `sidebar.py`, `backend/`, `web/` — netaknuto.
`day_view.py` je u `allowed_paths` (dodat radi konzistentnosti, dokumentovano
u planu prije koda).

### 6. Verifikacija (nezavisno ponovljena)

- `pytest tests/ -q` → **215 passed**
- `ruff check src/dentaland desktop tests` → All checks passed
- `mypy src/dentaland desktop backend` → **6 grešaka** (baseline, nula novih;
  sve postojeće `no-untyped-def`/`DragDrop` u week_view/main_window)

## Zaključak

Svi acceptance kriteriji zadovoljeni, data-safety (hard delete bez cascade)
dokazan statički i runtime-om, Enter-safety eksplicitan, scope čist. **PASS.**
