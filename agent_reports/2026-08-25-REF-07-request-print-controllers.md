---
task_id: REF-07
risk: LOW/MEDIUM
implementer: crush
reviewers: [codex, claude]
status: "READY FOR REVIEW — worktree REF-07-request-print-controllers, grana task/REF-07-request-print-controllers (sa main-a e251ad4)."
created_at: 2026-08-25
---

# REF-07 — Request i Print controller granice (implementer izvještaj)

## Šta je urađeno

Dovršen Controller sloj za request processing i print workflow.

### RequestController (`desktop/controllers/request_controller.py`, novo)

`process_pending_request` je premještena iz `requests_panel.py` (module-level
funkcija) u `RequestController.process_pending_request` (metoda, stateless —
drži samo `store`). Istovjetan dialog/business tok, samo sada u Controller sloju.

- `requests_panel.py`: uklonjena lokalna funkcija; `DashboardPanels` instancira
  `RequestController(store)` i `_confirm` delegira ka njemu.
- `requests_page.py`: uklonjen `from desktop.views.requests_panel import
  process_pending_request`; `RequestsPage` instancira `RequestController(store)`
  i `_process` delegira ka njemu.
- Zastareli komentar (requests_panel.py:19-20) o dvije `OverlapError` klase je
  uklonjen — od REF-01 je to JEDNA kanonizovana klasa; novi Controller importuje
  `from dentaland.services import OverlapError`.

Napomena: `from dentaland.services.requests import OverlapError` je ZADRŽAN u
`requests_panel.py` kao re-eksport (sa `# noqa: F401`), jer ga
`tests/test_ref00_overlap_error_contract.py::test_desktop_requests_panel_hvata_requests_klasu`
zaključava kao REF-01 invariant — nije ga dozvoljeno ukloniti.

### PrintController (`desktop/controllers/print_controller.py`, novo)

`_on_print`/`_print_week`/`_print_day`/`_save_pdf`/`_pick_day` premješteni iz
`MainWindow` u `PrintController` (prima `store`, `parent_widget`,
`week_start_provider`). `print_schedule.py` (servis) i `print_document.py`
ostaju netaknuti — Controller ih samo poziva.

`MainWindow` sada: konstruiše `PrintController(store, self, lambda:
self._schedule_controller.week_start)` i povezuje `print_action.triggered` i
print dugme na `print_controller.on_print`. Print metode su uklonjene iz
`MainWindow`; suvišni importi (`QDate`/`QCursor`/`QCalendarWidget`/`QDialog`/
`QDialogButtonBox`/`QFileDialog`/`QMenu` + print_schedule/print_document
funkcije) uklonjeni.

## Tačan mapping

```text
requests_panel.process_pending_request      → RequestController.process_pending_request
main_window._on_print                       → PrintController.on_print
main_window._print_week                     → PrintController.print_week
main_window._print_day                      → PrintController.print_day
main_window._save_pdf                       → PrintController.save_pdf
main_window._pick_day                       → PrintController._pick_day
```

## Izmjene GUI testova (obrazloženje)

Mehaničke izmjene import/monkeypatch putanje (mijenja se GDJE funkcija živi,
ne ŠTA testira):

- `tests/test_gui/test_requests_page.py` — `test_obrada_koristi_zajednicki_tok_i_osvjezava_listu`:
  monkeypatch sa `requests_page_mod.process_pending_request` na
  `RequestController.process_pending_request`; `fake_process` potpis `(self,
  request, parent)` umjesto `(actual_store, request, parent)`.
- `tests/test_gui/test_requests_panel.py` — monkeypatch `ProcessRequestDialog`
  sa `requests_panel` modula na `request_controller` modul (tamo je sada
  importovan); dodat import `request_controller as request_controller_mod`.

## Novi testovi

- `tests/test_gui/test_request_controller.py` (3) — None kad nema doktora;
  confirm poziva `confirm_pending`; reject poziva `reject_pending`.
- `tests/test_gui/test_print_controller.py` (3) — `print_week` zove
  build/preview; `save_pdf` koristi `getSaveFileName` + `pdf_path`; otkazano
  spremanje ne poziva preview.

## Verifikacija (stvaran output)

```text
$ python -m pytest tests/ -q
355 passed, 11 warnings in 12.27s

$ ruff check src/dentaland desktop backend tests
All checks passed!

$ mypy src/dentaland desktop backend
Success: no issues found in 45 source files
```

Baseline prije početka: 349 passed. Sada 355 (349 + 6 novih testova).

## Dirnuti fajlovi

```text
M  desktop/views/main_window.py
M  desktop/views/requests_page.py
M  desktop/views/requests_panel.py
M  tests/test_gui/test_requests_page.py
M  tests/test_gui/test_requests_panel.py
A  desktop/controllers/request_controller.py
A  desktop/controllers/print_controller.py
A  tests/test_gui/test_request_controller.py
A  tests/test_gui/test_print_controller.py
A  agent_reports/REF-07-task-contract.md
```

Nedirano (forbidden paths poštovan): `day_view.py`/`week_view.py`/
`desktop/presentation/**` (REF-06, Pi), `dialogs/**`, `services/**`,
`backend/**`, `models.py`, `migrations/**`.

## Napomene

- `desktop/controllers/__init__.py` nije trebao izmjenu (importi idu direktno,
  kao i za AppointmentController/ScheduleController).
- Task Contract je napisan nakon početka implementacije (priznato u njemu) —
  logika je čista ekstrakcija bez promjene ponašanja.
