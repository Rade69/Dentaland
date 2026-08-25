---
task_id: REF-06
risk: LOW
implementer: pi
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit 858b836, 2026-08-25), post-merge integration gate PASS (355 pytest, ruff, mypy)."
review_summary: >-
  Codex PASS, Claude PASS. desktop/presentation/ (schedule_status.py,
  schedule_palette.py) izdvojen kao jedina istina za status/paletu;
  day_view.py vise ne uvozi nista iz week_view.py. Backward-compat
  re-export u week_view.py (za main_window.py/dialogs koji su forbidden
  paths) dokazano ima stvarne potrosace, ne mrtav kod. Pronaden i
  prijavljen treci privatni simbol (WeekView._DOCTOR_PALETTE, koriscen u
  main_window.py) kao OUT_OF_SCOPE_FINDING, ne popravljen tiho.
created_at: 2026-08-25
merged_at: 2026-08-25
---

# REF-06 — Izdvojiti shared presentation logiku iz WeekView/DayView

## Task Contract

**Cilj:** `DayView` prestaje koristiti `WeekView` kao utility modul —
`day_view.py` ne importuje NIŠTA iz `week_view.py` (ni javno ni privatno).

**Risk:** `LOW`. Plan (sekcija 13) navodi `LOW/MEDIUM`; operativno klasifikujem
`LOW` jer je ovo behavior-preserving ekstrakcija čistih prezentacionih
konstanti/funkcija — bez promjene logike, bez servisnog sloja, bez baze, bez
API contracta. Dvostruki review (Codex + Claude) ostaje po dogovoru za REF
paket, nezavisno od risk oznake.

Izvor: `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`, sekcija 13.

Zavisnost: REF-05 — potvrđeno MERGED (main HEAD `e251ad4`).

## Dokazan problem (čitanjem koda, ne nagađanje)

`day_view.py:33`:

```python
from desktop.views.week_view import STATUS_META, WeekView, _status_key, status_icon
```

Dva privatna simbola preko granice modula:

1. `_status_key` — vodeći underscore, funkcija status→ključ (week_view.py:58).
2. `WeekView._DOCTOR_CARD_PALETTE` — day_view.py:272-273 pristupa DIREKTNO
   class-level atributu na konkretnoj klasi `WeekView` (week_view.py:99).

`WeekView` (konkretna klasa) je u day_view.py uvezena ISKLJUČIVO radi
`_DOCTOR_CARD_PALETTE` — grep potvrđuje da je to jedina upotreba imena
`WeekView` u day_view.py (linije 272-273).

## Impact analiza (grep po svim potrošačima)

| Simbol | Definiše | Potrošači |
|---|---|---|
| `STATUS_META` | week_view.py | day_view.py, dialogs/appointment_details.py, main_window.py, week_view.py |
| `STATUS_ORDER` | week_view.py | main_window.py, week_view.py |
| `_status_key` | week_view.py | day_view.py, dialogs/appointment_details.py, week_view.py |
| `status_icon` | week_view.py | day_view.py, tests/test_gui/test_week_view.py, week_view.py |
| `_status_visual` | week_view.py | SAMO week_view.py interno (ostaje tamo) |
| `WeekView._DOCTOR_CARD_PALETTE` | week_view.py (class attr) | day_view.py, week_view.py |
| `WeekView._DOCTOR_PALETTE` | week_view.py (class attr) | main_window.py:313, week_view.py interno |

**Testovi:** nijedan test ne referencira `_status_key` ni `_DOCTOR_CARD_PALETTE`
direktno (grep potvrđen). `test_week_view.py` uvozi `status_icon` — nastavlja
raditi jer week_view.py zadržava re-export.

## Arhitektonska promjena

1. `desktop/presentation/schedule_status.py` (novo) — `STATUS_META`,
   `STATUS_ORDER`, `status_key` (javna, bivša `_status_key`), `status_icon`.
2. `desktop/presentation/schedule_palette.py` (novo) — `DOCTOR_CARD_PALETTE`
   (javna konstanta, bivša `_DOCTOR_CARD_PALETTE`).
3. `desktop/presentation/__init__.py` (novo).
4. `week_view.py` — importuje iz presentation modula; zadržava module-level
   re-export `STATUS_META`/`STATUS_ORDER`/`status_icon` + alias
   `_status_key = status_key` (backward-compat); interno koristi
   `DOCTOR_CARD_PALETTE`. `_status_visual` ostaje privatna u week_view.py.
5. `day_view.py` — importuje iz presentation modula; `status_key` umjesto
   `_status_key`; `DOCTOR_CARD_PALETTE` umjesto `WeekView._DOCTOR_CARD_PALETTE`;
   ažurira docstring.

**Zašto re-export, a ne izmjena svih potrošača:** `main_window.py` i
`desktop/views/dialogs/**` su `forbidden_paths` za REF-06. Re-export drži
JEDNU istinu (definicija živi u presentation modulu, week_view je samo
proksi) bez diranja forbidden fajlova. Ovo nije dupliranje logike.

## Acceptance

- [ ] `day_view.py` ne importuje NIŠTA iz `week_view.py` (ni javno ni privatno);
- [ ] status/palette pravila su JEDNA istina (novi `desktop/presentation/` moduli), ne duplirana;
- [ ] DayView i WeekView ostaju odvojeni konkretni widgeti;
- [ ] nema mega-base klase;
- [ ] postojeći GUI testovi prolaze (nema izmjena testova — potvrđeno grep-om).

## Allowed paths

```text
desktop/presentation/schedule_status.py     (novo)
desktop/presentation/schedule_palette.py    (novo)
desktop/presentation/__init__.py            (novo)
desktop/views/day_view.py
desktop/views/week_view.py
tests/test_gui/test_day_view.py             (samo ako nužno, obrazloži)
tests/test_gui/test_week_view.py            (isto)
agent_reports/**
```

## Forbidden paths

```text
desktop/views/main_window.py        (provjereno: ne moram ga dirati — re-export pokriva)
desktop/controllers/**
desktop/views/dialogs/**
src/dentaland/services/**
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

Baseline izmjeren na ovom worktree-u prije koda: **349 passed**.

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

## Review

Codex (test kvalitet, prvi) pa Claude (arhitektura). Radovan human approval
obavezan prije merge-a.

## Koordinacija

Worktree `Dentaland-worktrees/REF-06-presentation-split`, grana
`task/REF-06-presentation-split` (sa main-a `e251ad4`). Claim postavljen
prije koda.
