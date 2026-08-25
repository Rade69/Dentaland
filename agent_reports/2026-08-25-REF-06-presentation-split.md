---
task_id: REF-06
risk: LOW
implementer: pi
reviewers: [codex, claude]
status: "IMPLEMENTED — čeka review. Bez commit-a (pravilo: nikad commit bez eksplicitnog zahtjeva)."
verification: "pytest 349 passed (baseline 349), ruff All checks passed, mypy no issues in 46 files."
created_at: 2026-08-25
---

# REF-06 — Implementer izvještaj (Pi)

## Šta je urađeno

`DayView` više ne koristi `WeekView` kao utility modul. Status i paleta
pravila su izdvojeni u novi `desktop/presentation/` paket (jedna istina);
`week_view.py` ih ponovo izlaže radi backward-compat sa fajlovima koji su
`forbidden_paths` za ovaj task.

## Tačan spisak premještenih simbola

| Stari simbol | Novi simbol | Iz | U |
|---|---|---|---|
| `STATUS_META` | `STATUS_META` (isto) | `week_view.py:47` | `presentation/schedule_status.py` |
| `STATUS_ORDER` | `STATUS_ORDER` (isto) | `week_view.py:55` | `presentation/schedule_status.py` |
| `_status_key` | `status_key` (javna) | `week_view.py:58` | `presentation/schedule_status.py` |
| `status_icon` | `status_icon` (isto) | `week_view.py:73` | `presentation/schedule_status.py` |
| `WeekView._DOCTOR_CARD_PALETTE` | `DOCTOR_CARD_PALETTE` (javna konstanta) | `week_view.py:99` (class attr) | `presentation/schedule_palette.py` |

## Namjerno NIJE premješteno

- `_status_visual` — ostaje privatna u `week_view.py` (jedini potrošač je
  `week_view.py` interno; nije shared). Sada koristi uvezenu `status_key`.
- `WeekView._DOCTOR_PALETTE` — ostaje class attr u `week_view.py` (vidi
  `OUT_OF_SCOPE_FINDING` niže).

## Backward-compat re-export u week_view.py

```python
STATUS_ORDER = _STATUS_ORDER   # main_window.py uvozi STATUS_ORDER iz week_view
_status_key = status_key       # dialogs/appointment_details.py uvozi _status_key
```

Razlog: `desktop/views/main_window.py` i `desktop/views/dialogs/**` su
`forbidden_paths` za REF-06. Re-export NIJE dupliranje logike — definicija
živi isključivo u `presentation/`, week_view je samo proksi. Grep potvrđuje
potrošače: main_window.py uvozi `STATUS_META, STATUS_ORDER`, a
appointment_details.py uvozi `STATUS_META, _status_key`.

## Obrazloženje izmjena po fajlu

### `desktop/views/day_view.py`

- Import `from desktop.views.week_view import ...` → `from
  desktop.presentation.schedule_status import ...` + `from
  desktop.presentation.schedule_palette import ...`.
- `_status_key(appt)` → `status_key(appt)` (2 mjesta: `visible_status_counts`,
  `_open_context_menu`).
- U `_open_context_menu` lokalna varijabla `status_key` preimenovana u `key`
  — nova uvezena funkcija `status_key` bi bila zasjenjena lokalnom varijablom
  istog imena (UnboundLocalError). Ovo je jedina "logička" izmjena u fajlu,
  i behavior-preserving je.
- `WeekView._DOCTOR_CARD_PALETTE[...]` → `DOCTOR_CARD_PALETTE[...]` (jedina
  upotreba klase `WeekView` u day_view.py — time cijeli `WeekView` uvoz
  nestaje, potvrđeno grep-om prije i poslije).
- Docstring ažuriran: "helpere iz ``week_view``" → "konstante iz
  ``desktop.presentation``".

### `desktop/views/week_view.py`

- Obrisane definicije `STATUS_META`, `STATUS_ORDER`, `_status_key`,
  `status_icon` i class attr `_DOCTOR_CARD_PALETTE`; dodani importi iz
  `presentation/` + re-export (gore).
- `refresh()`: `self._DOCTOR_CARD_PALETTE[...]` → `DOCTOR_CARD_PALETTE[...]`.
- `_status_visual()`: `STATUS_META[_status_key(appt)]` →
  `STATUS_META[status_key(appt)]`.

## Testovi — NEMA izmjena

Grep `_status_key\|_DOCTOR_CARD_PALETTE` kroz `tests/` prije početka: nijedan
test ne referencira te simbole direktno. `test_week_view.py` uvozi
`status_icon` iz `week_view` — nastavlja raditi jer week_view zadržava
re-export. Nula izmjena test fajlova.

## Verifikacija (doslovni rezultati)

```text
$ python -m pytest tests/ -q
349 passed, 11 warnings in 14.76s        (baseline prije koda: 349 passed)

$ python -m ruff check src/dentaland desktop backend tests
All checks passed!

$ python -m mypy src/dentaland desktop backend
Success: no issues found in 46 source files   (43 → 46 zbog 3 nova fajla)
```

## Acceptance

- [x] `day_view.py` ne importuje ništa iz `week_view.py` — grep potvrđen
  (preostale "WeekView" reference u docstringu su opisne, ne uvoz).
- [x] status/palette pravila su jedna istina u `desktop/presentation/`.
- [x] DayView i WeekView ostaju odvojeni konkretni widgeti.
- [x] nema mega-base klase (nije dodato ništa slično `BaseSchedulerView`).
- [x] postojeći GUI testovi prolaze bez izmjena.

## OUT_OF_SCOPE_FINDING

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  main_window.py:313 pristupa WeekView._DOCTOR_PALETTE direktno (privatni
  class atribut preko granice modula) — isti tip arhitektonskog duga kao
  _DOCTOR_CARD_PALETTE, ali main_window.py je forbidden_path za REF-06.
location: desktop/views/main_window.py:313
risk: LOW
proposed_task: REF-XX — izdvojiti DOCTOR_PALETTE u desktop/presentation/schedule_palette.py
```

## Nije urađeno / namjerno izostavljeno

- Nema commit-a — po pravilu, čekam eksplicitan zahtjev.
- `desktop/views/main_window.py`, `desktop/controllers/**`,
  `desktop/views/dialogs/**` nisu dirani (forbidden_paths, potvrđeno da ne
  moraju — re-export pokriva).
