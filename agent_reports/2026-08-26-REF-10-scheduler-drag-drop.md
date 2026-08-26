---
task_id: REF-10
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: "IMPLEMENTED — čeka review. Bez commit-a (eksplicitna instrukcija: čekati Radovanov zahtjev)."
verification: "pytest 364 passed, ruff All checks passed, mypy no issues in 51 files."
created_at: 2026-08-26
---

# REF-10 — Implementer izvještaj (Pi)

## Šta je urađeno

Scheduler drag&drop (`move_appointment_to_slot` u `day_view.py`/`week_view.py`)
više ne poziva `self.store.move(...)` direktno — ide kroz `AppointmentController`
(nalaz F1 iz finalnog acceptance audita). `dropEvent`-om pokretana sinhrona
`bool` logika je behavior-preserving: na `OverlapError` i dalje tih
`event.ignore()`, bez ikakvog dijaloga.

## Izmjene (po kontraktu)

### desktop/controllers/appointment_controller.py

- Nova čista metoda (bez dijaloga):
  `move_appointment_slot(appt_id, new_start, new_end) -> bool` — poziva
  `store.move`, na `OverlapError` vraća `False`, inače `True`.
- `_parent_widget` prebačen sa jake reference na weak referencu (vidi
  OUT_OF_SCOPE_FINDING F2 niže — nužna korekcija, ne širenje scope-a).

### desktop/views/day_view.py + week_view.py

- Import `AppointmentController` + `self._appointment_controller =
  AppointmentController(store, self, lambda: None)` u `__init__` (kontraktov
  obrazac, `refresh_callback` no-op — refresh ide kroz postojeći
  `appointment_moved` signal, netaknut).
- `move_appointment_to_slot`: samo `try/except OverlapError` blok zamijenjen sa
  `if not self._appointment_controller.move_appointment_slot(...): return False`.
  Sve ostalo (occupancy/doctor-kolona provjere, `appointment_moved.emit`,
  `return True`) netaknuto.
- `main_window.py` NIJE diran (signal konekcije `appointment_moved` ostale
  netaknute).

## OUT_OF_SCOPE_FINDING (2 nalaza — kontrakt korekcije, oba nužna)

### F1 — OverlapError mora ostati kao re-eksport (kontrakt je rekao "ukloni")

Kontrakt tačka 4 traži uklanjanje `OverlapError` iz importa. To bi pokvarilo
`tests/test_ref00_overlap_error_contract.py`
(`test_desktop_day_view_hvata_booking_klasu` / `..._week_view_...`) koji
eksplicitno zahtijeva `day_view.OverlapError` / `week_view.OverlapError`
re-eksport (REF-00/01 characterization contract).

Rješenje: `OverlapError` ZADRŽAN kao re-eksport sa `# noqa: F401` (isti obrazac
kao `requests_panel.py`). NIJE korišten u logici — samo izložen.

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  Kontraktova instrukcija "ukloniti OverlapError import" je u konfliktu sa
  REF-00 contract testom koji zahtijeva re-eksport. Zadržano kao re-eksport.
location: desktop/views/day_view.py, desktop/views/week_view.py (import)
risk: LOW
proposed_task: none (re-eksport je ispravan stalni oblik)
```

### F2 — reference ciklus View ↔ AppointmentController (kontraktov `self`)

Kontraktov oblik `AppointmentController(store, self, lambda: None)` stvara
reference ciklus (`WeekView._appointment_controller` ↔
`AppointmentController._parent_widget`), što odlaže Python GC i ruši
`tests/test_gui/test_schedule_controller.py`
(`test_pravi_viewovi_ne_fetchuju_interno`, `test_pravi_day_view_ne_fetchuje_interno`)
pri teardown: `RuntimeError: libshiboken: Internal C++ object (WeekView)
already deleted`. Adversarno potvrđeno: uklanjanje instance → testovi prolaze;
sa instancom → 2 errors.

Rješenje: `_parent_widget` postaje weak referenca (sa jakim closure fallback-om
za ne-weakref-able objekte poput `SimpleNamespace` u testovima). Ovo je unutar
`allowed_paths` (`appointment_controller.py`), behavior-preserving (property
vraća isti parent dok je živ), i razbija ciklus na izvoru — kontraktov `self`
ostaje netaknut.

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  Kontraktov oblik (parent_widget=self) stvara reference ciklus koji ruši
  postojeći teardown test. _parent_widget prebačen na weakref sa fallback-om.
location: desktop/controllers/appointment_controller.py (__init__ + property)
risk: MEDIUM
proposed_task: none (weakref je ispravan stalni oblik)
```

## Testovi (dodato proaktivno, po kontrakt "Upozorenje o test kvalitetu")

2 nova testa (po jedan za svaki view) — zaključavaju da `move_appointment_to_slot`
ide kroz Controller, ne direktan `store.move`:

- `tests/test_gui/test_day_view.py::test_move_ide_kroz_appointment_controller`
- `tests/test_gui/test_week_view.py::test_move_ide_kroz_appointment_controller`

Obrazac: monkeypatch `view._appointment_controller.move_appointment_slot` spy-em
koji vraća `True` i beleži `(appt_id, new_start, new_end)`; assert tačan poziv +
da `store` podatak NIJE promijenjen (spy ne poziva `store.move`).

**Adversarni dokaz:** privremeno vraćen direktan `self.store.move(...)` u oba
view-a → oba nova testa **FAIL** (`calls == []`). Controller verzija vraćena →
oba **PASS**. Testovi genuinski padaju na starom F1 obrascu.

## Verifikacija (doslovni rezultati)

```text
$ python -m pytest tests/ -q
364 passed, 11 warnings in 10.60s

$ python -m ruff check src/dentaland desktop backend tests
All checks passed!

$ python -m mypy src/dentaland desktop backend
Success: no issues found in 51 source files
```

## Acceptance

- [x] `day_view.py`/`week_view.py` više ne sadrže `self.store.move(...)`
      (grep `self\.store\.move` → 0);
- [x] ponašanje na `OverlapError` identično (tih `event.ignore()`, bez
      dijaloga) — `move_appointment_slot` samo vraća `False`;
- [x] `main_window.py` NIJE diran (nije u `git diff --stat`);
- [x] postojeći drag&drop testovi prolaze + 2 nova Controller-ruta testa;
- [x] `pytest`, `ruff`, `mypy` čisti.

## Nije urađeno / namjerno izostavljeno

- Nema commit-a — čekam Radovanov zahtjev.
- `main_window.py`, `requests_panel.py`, `blockout_panel.py`, `settings_panel.py`,
  ostali controlleri i forbidden paths nisu dirani.
- Nije mijenjan nijedan servisni fajl (`src/dentaland/services/**`).
