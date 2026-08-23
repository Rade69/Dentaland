---
task_id: FIX-09
risk: LOW
implementer: codex
reviewers: [claude]
verdict: "MERGED → INTEGRATION_VERIFIED → DONE (merge 6b3196c). Human approval: Radovan. Post-merge gate: pytest 287 passed, ruff clean, mypy clean (0 issues, 36 fajlova)."
commits: [7f1386f, 6b3196c]
created_at: 2026-08-22
---

# Task Contract — novi dizajn stranice „Novi zahtjevi“

```yaml
id: FIX-09
title: Redizajnirati desktop stranicu za nove online zahtjeve
risk: LOW
objective: Uskladiti RequestsPage sa dostavljenim dashboard dizajnom bez promjene toka obrade zahtjeva.
allowed_paths:
  - desktop/views/requests_page.py
  - desktop/views/main_window.py
  - tests/test_gui/test_requests_page.py
  - agent_reports/FIX-09-task-contract.md
  - agent_reports/2026-08-22-FIX-09-new-requests-design.md
forbidden_paths:
  - desktop/views/requests_panel.py
  - desktop/views/dialogs/process_request.py
  - src/dentaland/
  - backend/
  - migrations/
acceptance:
  - stranica ima naslov, podnaslov, summary karticu i donji savjet kao na referenci
  - svaki zahtjev prikazuje inicijale, ime, telefon, email, traženi datum, vrijeme slanja, NOVO oznaku i Obradi dugme
  - lista se skroluje i ostaje upotrebljiva sa više zahtjeva na 1536 x 760
  - Obradi koristi postojeći process_pending_request tok i nakon uspjeha osvježava listu
  - prazno stanje ostaje jasno i funkcionalno
verification:
  - pytest tests/test_gui/test_requests_page.py -q
  - pytest tests/test_gui/test_main_window.py -q
  - ruff check desktop/views/requests_page.py desktop/views/main_window.py tests/test_gui/test_requests_page.py
```

## Scope

Vizuelni i layout redizajn postojeće `RequestsPage`, deterministički GUI
testovi i stvarni Qt smoke render.

## Out of scope

Backend/service semantika, dijalog obrade, dashboard panel desno na kalendaru,
novi meni akcija iza dekorativne tri-tačke kontrole i izmjene podataka.
