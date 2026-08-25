---
task_id: REF-07
risk: LOW/MEDIUM
implementer: crush
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit f541e0a, 2026-08-25), post-merge integration gate PASS (355 pytest, ruff, mypy)."
review_summary: >-
  Codex PASS_WITH_NOTES, Claude PASS_WITH_NOTES. RequestController i
  PrintController (novo) preuzeli su process_pending_request iz
  requests_panel.py i print workflow iz MainWindow-a, ponasanje
  identicno preneseno (potvrdjeno oba reviewera nezavisno). OverlapError
  re-export u requests_panel.py dokazano stvaran (REF-00 contract test).
  PrintController week_start_provider callable DI istaknut kao bolji
  obrazac od REF-04/05 kompromisa - preporuceno kao model za REF-08.
  Non-blocking: print testovi ne pokrivaju on_print/print_day/_pick_day
  (poznat gap, ne blokira).
created_at: 2026-08-25
merged_at: 2026-08-25
---

# REF-07 — Request i Print controller granice

## Task Contract

**Cilj:** dovršiti Controller sloj — premjestiti `process_pending_request` u
`RequestController`, a print workflow (`_on_print`/`_print_week`/`_print_day`/
`_save_pdf`/`_pick_day`) iz `MainWindow` u `PrintController`. View-ovi
(`requests_panel.py`/`requests_page.py`) pozivaju Controller umjesto lokalne
funkcije; `MainWindow` više ne nosi detaljan print workflow.

**Risk:** LOW/MEDIUM (čista ekstrakcija postojeće logike, bez promjene
ponašanja; dvostruki review za REF paket).

Izvor: `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`, sekcija 14.

Zavisnost: REF-04 (MERGED). Paralelno Pi radi REF-06 (day_view/week_view/
presentation) — scope-ovi se ne preklapaju; claim SAMO svoje fajlove
(potvrđeno `coordination.py status`, nema konflikta).

## Nalazi (potvrđeno čitanjem koda)

1. `process_pending_request(store, request, parent)` (requests_panel.py:25-53)
   je samostalna funkcija; pozivaju je `requests_page.py:230` i
   `requests_panel.py:186` direktno iz View fajlova. `MainWindow` je nikad ne
   poziva (samo instancira RequestsPage/DashboardPanels). Premjestiti u
   `RequestController.process_pending_request` kao metodu.
2. Zastareli komentar (requests_panel.py:19-20) o `requests.OverlapError` vs
   `booking.OverlapError` — poslije REF-01 to je ISTA kanonizovana klasa;
   ukloniti (novi Controller koristi `from dentaland.services import OverlapError`).
3. Print workflow (`main_window.py:644-701`): `_on_print`/`_print_week`/
   `_print_day`/`_save_pdf`/`_pick_day`. Premjestiti u `PrintController`
   (prima `store`, `parent_widget`, `week_start_provider`).

## Acceptance

- [ ] `MainWindow` ne nosi detaljan print workflow;
- [ ] `process_pending_request` živi u `RequestController`, ne u `requests_panel.py`;
- [ ] request business rules ostaju u `services/requests.py` (nedirano);
- [ ] print data priprema ostaje u `services/print_schedule.py` (nedirano);
- [ ] postojeći GUI testovi prolaze (ažurirati samo ako direktno pozivaju premještene funkcije — obrazložiti).

## Allowed paths

```text
desktop/controllers/request_controller.py    (novo)
desktop/controllers/print_controller.py      (novo)
desktop/controllers/__init__.py
desktop/views/main_window.py
desktop/views/requests_page.py
desktop/views/requests_panel.py
tests/test_gui/test_request_controller.py    (novo)
tests/test_gui/test_print_controller.py      (novo)
tests/test_gui/test_requests_page.py         (samo ako nužno)
tests/test_gui/test_requests_panel.py        (isto)
agent_reports/**
```

## Forbidden paths

```text
desktop/views/day_view.py        (REF-06, Pi — NE DIRATI)
desktop/views/week_view.py       (isto)
desktop/presentation/**          (REF-06 novi moduli)
desktop/views/dialogs/**         (ProcessRequestDialog se poziva, ne mijenja)
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

Baseline: **349 pytest passed** (izmjeriti tačan broj na svom worktree-u prije
početka).

## Review

Codex (test kvalitet, prvi) pa Claude (arhitektura). Radovan human approval.

## Koordinacija

Worktree `Dentaland-worktrees/REF-07-request-print-controllers`, grana
`task/REF-07-request-print-controllers` (sa main-a `e251ad4`). Claim prije
početka; nema konflikta sa Pi (REF-06).

## Napomena (transparentno)

Task Contract je napisan NAKON što je implementacija započeta (priznata
greška u redoslijedu, isti obrazac kao REF-04). Logika je čista ekstrakcija
bez promjene ponašanja.
