---
task_id: REF-11
risk: LOW
implementer: crush
reviewers: [codex, claude]
status: "READY FOR REVIEW — implementacija + verifikacija gotovi (355 pytest, ruff, mypy čisti). NIJE commitovano (čeka Radovanov zahtjev)."
created_at: 2026-08-25
---

# REF-11 — BlockoutController (F2) — implementer izvještaj

## Šta je urađeno

Po Task Contract-u (`agent_reports/REF-11-task-contract.md`):

- Nov `desktop/controllers/blockout_controller.py` — `BlockoutController`
  klasa, čista delegacija (facade) na store, bez logike:
  - `create_time_off(doctor_id, start, end, reason)` → `store.create_time_off(...)`
  - `delete_time_off(block_id)` → `store.delete_time_off(...)`
- `desktop/views/blockout_panel.py`:
  - `BlockoutPanel.__init__` konstruiše privatnu instancu
    `self._blockout_controller = BlockoutController(store)` (isti obrazac kao
    `RequestController(store)` iz REF-07).
  - `_on_save` (linija 181): `self.store.create_time_off(...)` →
    `self._blockout_controller.create_time_off(...)`.
  - `_on_delete` (linija 195): `self.store.delete_time_off(...)` →
    `self._blockout_controller.delete_time_off(...)`.
  - `try`/`except` (`OverlapError`/`ValueError`), `_show_error`, `refresh`,
    `changed.emit()` — **netaknuti** (View-specifična inline prezentacija
    greške, Controller ostaje tanak).

## Acceptance dokaz

```text
$ grep -n "self\.store\.create_time_off\|self\.store\.delete_time_off" desktop/views/blockout_panel.py
(bez rezultata — mutacijski pozivi uklonjeni)

$ grep -n "self\.store\." desktop/views/blockout_panel.py
(bez rezultata — nema `self.store.<metoda>()` poziva)
```

Preostali `self.store` (samo READ, kroz `getattr`): `doctors` (linija 111) i
`list_time_off` (linija 126) — nisu mutacijski, contract dozvoljava.

## Verifikacija (stvaran output)

```text
$ python -m pytest tests/ -q
355 passed, 11 warnings in 33.86s

$ ruff check src/dentaland desktop backend tests
All checks passed!

$ mypy src/dentaland desktop backend
Success: no issues found in 51 source files
```

## Dirnuti fajlovi

```text
A  desktop/controllers/blockout_controller.py
M  desktop/views/blockout_panel.py
A  agent_reports/2026-08-25-REF-11-blockout-controller.md
```

Nedirano (forbidden paths poštovan): `main_window.py`, `settings_panel.py`,
`requests_panel.py`, `day_view.py`, `week_view.py`, `appointment_controller.py`,
`schedule_controller.py`, `settings_controller.py`, `services/**`, `models.py`,
`migrations/**`, `backend/**`.

## OUT_OF_SCOPE_FINDING

Nema.

## Napomena

NIJE commitovano/pušovano (po instrukciji — čeka Radovanov zahtjev).
