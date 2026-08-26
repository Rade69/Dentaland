---
task_id: REF-09
risk: LOW
implementer: pi
reviewers: [codex, claude]
status: "IMPLEMENTED + test fix nakon Codex REJECT (F1) — čeka re-review. Bez commit-a."
verification: "pytest 357 passed (355 + 2 nova), ruff All checks passed, mypy no issues in 50 files."
created_at: 2026-08-25
---

# REF-09 — Implementer izvještaj (Pi)

## Šta je urađeno

`DashboardPanels` (desktop/views/requests_panel.py) više ne poziva
`self.store.mark_confirmed`/`self.store.cancel` direktno — akcije "Potvrdi"/
"Odbaci" sada idu kroz postojeći `AppointmentController` (nalaz F4 iz finalnog
acceptance audita). Mehanizam je ožičavanje postojeće, već testirane Controller
logike — nula nove poslovne logike.

## Izmjene (tačno po kontraktu)

### desktop/controllers/appointment_controller.py

`method_map` u `handle_appointment_action` — dodat novi ključ:

```python
method_map = {
    "confirm": "mark_confirmed",
    "reject": "cancel",        # NOVO — bezdijaloški (dashboard "Odbaci")
    "arrived": "mark_arrived",
    ...
}
```

Postojeći dijalog-bazirani `"cancel"` flow (`if action == "cancel":` +
`cancel_appointment()`) je NETAKNUT — `"reject"` je odvojen ključ koji mapira
direktno na store `cancel(appt_id)` (bezdijaloški), analogno `"confirm"` →
`mark_confirmed`.

### desktop/views/requests_panel.py

- Import: `from desktop.controllers.appointment_controller import AppointmentController`.
- `__init__`: `self._appointment_controller = AppointmentController(store, self,
  self._on_appointment_changed)` — ista privatna-instancija obrazac kao
  postojeći `self._request_controller = RequestController(store)`.
- Nova metoda `_on_appointment_changed` = `self.refresh(); self.changed.emit()`
  (tačno ono što su `_confirm_scheduled`/`_cancel_scheduled` ranije radili
  nakon mutacije).
- `_confirm_scheduled` → `self._appointment_controller.handle_appointment_action(appt_id, "confirm")`.
- `_cancel_scheduled` → `self._appointment_controller.handle_appointment_action(appt_id, "reject")`.

## Ponašanje NIJE promijenjeno

- Dashboard "Potvrdi"/"Odbaci" i dalje rade BEZ potvrdnog dijaloga (isti UX).
  `"reject"` → store `cancel` direktno, ne `cancel_appointment()` (koji otvara
  dijalog) — kako kontrakt eksplicitno zahtijeva.
- `AppointmentController._parent_widget` je ovdje `DashboardPanels` (ne
  `MainWindow`) — bezopasno: `method_map` grana (`confirm`/`reject`) ne čita
  `_doctors`/`_has_doctors`/`_current_doctor_id` (potvrđeno čitanjem koda).
- `changed` signal se i dalje emituje kroz `_on_appointment_changed` — svi
  slušači (`main_window.py` itd.) rade kao prije.

## Acceptance

- [x] `requests_panel.py` više ne sadrži `self.store.mark_confirmed`/
      `self.store.cancel` pozive (potvrđeno);
- [x] `grep -n "self\.store\." desktop/views/requests_panel.py` → **0**
      pogodaka (čak i strožije od traženog: `_call()` koristi
      `getattr(self.store, name, None)`, ne `self.store.` — read-only pozivi
      `pending_requests`/`awaiting_confirmation`/`cancelled_today` netaknuti);
- [x] postojeći GUI testovi prolaze BEZ izmjene — `test_klik_na_potvrdi_zove_mark_confirmed_i_uklanja_stavku`
      i `test_klik_na_odbaci_zove_cancel_i_uklanja_stavku` (test_requests_panel.py)
      i dalje hvataju `store.mark_confirmed`/`store.cancel` kroz controller;
- [x] `pytest tests/ -q`, `ruff check`, `mypy` čisti.

## Verifikacija (doslovni rezultati)

```text
$ python -m pytest tests/ -q
355 passed, 11 warnings in 29.42s

$ python -m ruff check src/dentaland desktop backend tests
All checks passed!

$ python -m mypy src/dentaland desktop backend
Success: no issues found in 50 source files
```

## OUT_OF_SCOPE_FINDING

Nema. Kontraktova napomena (da li `_refresh_dashboard` pokriva sve što je
`changed.emit()` ranije radio) je provjerena: `changed.emit()` je i dalje
emitovan kroz `_on_appointment_changed`, pa nema promjene u signalnoj
topologiji. Nema skrivenog slušača koji bi izgubio signal.

## Fix nakon Codex REJECT (F1 — test kvalitet)

Codex je adversarno dokazao da postojeća dva testa
(`test_klik_na_potvrdi_zove_mark_confirmed_i_uklanja_stavku`,
`test_klik_na_odbaci_zove_cancel_i_uklanja_stavku`) daju lažan PASS na starom
direktnom `self.store.*` obrascu — provjeravaju samo krajnje stanje, ne PUT.

Dodata dva nova testa u `tests/test_gui/test_requests_panel.py`:
- `test_potvrdi_ide_kroz_appointment_controller` — monkeypatch
  `panels._appointment_controller.handle_appointment_action`, klik "Potvrdi",
  assert poziv `(7, "confirm")`; `store.mark_confirmed` postavljen da baca ako
  se pozove direktno.
- `test_odbaci_ide_kroz_appointment_controller_bezdijaloski` — isto za
  "Odbaci", assert `(7, "reject")`; `store.cancel` postavljen da baca.

Adversarna provjera (uradio je implementer, kao Codex): privremeno vraćen
stari direktni poziv u `_confirm_scheduled`/`_cancel_scheduled`, pokrenuta oba
nova testa → **2 failed, 2 errors** (`AssertionError: direktan store.* poziv
(mimo Controllera)`). Controller verzija vraćena, oba testa → **2 passed**.

Nova dva testa su time dokazano genuinske regresijske mreže za F4 invariant
(View → Controller, bezdijaloški `reject`).

## Nije urađeno / namjerno izostavljeno

- Nema commit-a — po instrukciji, čekam Radovanov zahtjev.
- `main_window.py`, `day_view.py`, `week_view.py`, ostali controlleri i
  forbidden_paths nisu dirani (nulto preklapanje sa REF-11/12/13).
- Nije mijenjan nijedan test fajl.
