# Implementer izveštaj — DENT-019 (mypy cleanup main_window.py)

Task: DENT-019 | Risk: LOW | Implementer: pi | Status: IMPLEMENTED (čeka review)

## Validacija `.agent/` sloja (prije prve izmjene)

- **Fajlova pročitano prije 1. izmjene**: 4 — `agent_reports/DENT-019-task-contract.md`,
  `.agent/PROJECT_MAP.md`, `.agent/TASK_ROUTING.md`, `desktop/views/main_window.py`
  (relevantne linije 45–60 i 535–545).
- **Koristio `.agent/`?** DA — ovaj put direktno iz `main` (sloj je merge-ovan;
  `git ls-files .agent/` vraća sva 4 fajla). `TASK_ROUTING.md` ("Bug task") je
  potvrdio read-set, `PROJECT_MAP.md` je dao domenu (`main_window.py` → Desktop
  scheduler). Nula `ls`/`find` istraživačkih poziva.
- **Pitao za pojašnjenje strukture?** NE.
- **Prekršio scope?** NE (samo `desktop/views/main_window.py`).

## Plan

Ukloniti 2 mypy greške (no-untyped-def) bez promjene ponašanja:
1. `__init__(self, store, week_start=None, parent=None)` → `store: Any`,
   `parent: QWidget | None` (store je duck-typed — FakeStore/AppointmentService
   preko getattr, `Any` opravdan kao kod `_edit_appointment(appt: Any)`; parent
   ide u `super().__init__`).
2. `_on_slot_selected(self, start)` → `start: datetime` (pozivaoci: `_on_new_appointment`
   i `slot_selected` signal — oba emituju `datetime`).

## Verifikacija

```
mypy desktop backend src/dentaland   → 4 errors, SVE u week_view.py; NULA u main_window.py
pytest tests/test_gui/test_main_window.py -q  → 20 passed
ruff check desktop/views/main_window.py  → All checks passed!
```

Napomena: `mypy desktop/views/main_window.py` samostalno ne nalazi `dentaland`
importe (pyproject nema `mypy_path`; pytest-ov `pythonpath` se ne odnosi na mypy) —
uz `MYPYPATH="src;."` prati importe i ne prijavljuje NITI JEDNU grešku u
`main_window.py` (samo transitivne `week_view.py` greške, koje su DENT-018,
ne ovaj task). Obje ciljne greške (linija 52 i 540) su uklonjene.

## Scope potvrda

`git status` — samo `desktop/views/main_window.py` izmijenjen (plus ovaj report).
