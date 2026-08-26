---
task_id: REF-14
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: "IMPLEMENTED — čeka review. Bez commit-a (eksplicitna instrukcija: čekati zahtjev)."
verification: "pytest 374 passed, ruff All checks passed, mypy no issues in 52 files, agent_sensors 0 blocking findings."
created_at: 2026-08-26
---

# REF-14 — Implementer izvještaj (Pi)

## Šta je urađeno

`AppointmentController` više ne čita doctor-state kroz `getattr` pogađanje
imena privatnih atributa na `parent_widget` — umjesto toga koristi tri
eksplicitna, tipizirana keyword-only provider callable-a. Plus uklonjen mrtav
`ScheduleController._current_doctor_id`.

## Izmjene (po kontraktu)

### desktop/controllers/appointment_controller.py

Konstruktor dobija tri OPCIONA keyword-only parametra sa safe default-ima
(identično dosadašnjem getattr fallback-u):

```python
*,
doctors_provider: Callable[[], list] = lambda: [],
has_doctors_provider: Callable[[], bool] = lambda: False,
current_doctor_id_provider: Callable[[], int | None] = lambda: None,
```

Metode `_doctors()`/`_has_doctors()`/`_current_doctor_id()` sada delegiraju
na providere umjesto na `getattr(self._parent_widget, ...)`. `_parent_widget`
(weakref, REF-10) OSTAJE — i dalje se koristi za Qt dialog/`QMessageBox`
parenting.

### desktop/controllers/schedule_controller.py

Uklonjeno mrtvo polje: `self._current_doctor_id: int | None = None` (u
`__init__`) i `self._current_doctor_id = doctor_id` (u `set_doctor_filter`).
`set_doctor_filter` i dalje radi identično (`self._week_view.set_filter(...)`
+ `self.refresh()`).

### desktop/views/main_window.py

Jedino mjesto koje stvarno treba doctor state prosljeđuje providere
eksplicitno:

```python
self._controller = AppointmentController(
    store, self, self._refresh_dashboard,
    doctors_provider=lambda: self._doctors,
    has_doctors_provider=lambda: self._has_doctors,
    current_doctor_id_provider=lambda: self._current_doctor_id,
)
```

## Acceptance

- [x] `schedule_controller.py` više ne sadrži `_current_doctor_id` (grep 0);
- [x] `appointment_controller.py` čita doctor-state isključivo kroz provider-e
      (grep `getattr(self._parent_widget` → 0);
- [x] `main_window.py` prosljeđuje sva tri providera;
- [x] `day_view.py`/`week_view.py`/`requests_panel.py` OSTAJU NETAKNUTI —
      `git status` pokazuje samo 3 fajla (appointment_controller,
      schedule_controller, main_window);
- [x] postojeći GUI testovi prolaze bez izmjene (374 passed);
- [x] `pytest`, `ruff`, `mypy`, `agent_sensors` čisti.

## Verifikacija (doslovni rezultati)

```text
$ python -m pytest tests/ -q
374 passed, 11 warnings in 21.14s

$ python -m ruff check src/dentaland desktop backend tests scripts/agent_sensors.py
All checks passed!

$ python -m mypy src/dentaland desktop backend
Success: no issues found in 52 source files

$ python scripts/agent_sensors.py --all
Result: 0 blocking findings
```

## Nije urađeno / namjerno izostavljeno

- Nema commit-a — čekam zahtjev.
- `day_view.py`, `week_view.py`, `requests_panel.py`, `blockout_panel.py`,
  `settings_panel.py`, ostali controlleri i forbidden paths nisu dirani.
- `_parent_widget` weakref (REF-10) nije mijenjan — i dalje potreban za Qt
  parenting.
