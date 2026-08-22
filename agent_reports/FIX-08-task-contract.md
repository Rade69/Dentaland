---
task_id: FIX-08
risk: LOW
implementer: codex
reviewers: [independent]
verdict: PENDING
commits: []
created_at: 2026-08-22
---

# Task Contract — avatari doktora 56 px

```yaml
id: FIX-08
title: Povećati avatere doktora sa 48 na 56 px
risk: LOW
objective: Poboljšati čitljivost fotografija doktora bez narušavanja desnog panela na laptop rezoluciji.
allowed_paths:
  - desktop/views/main_window.py
  - tests/test_gui/test_main_window.py
  - agent_reports/FIX-08-task-contract.md
  - agent_reports/2026-08-22-FIX-08-doctor-avatar-56.md
forbidden_paths:
  - desktop/assets/doctors/
  - desktop/views/requests_panel.py
  - src/dentaland/
  - migrations/
acceptance:
  - sva tri avatara su tačno 56 x 56 px
  - imena i brojčane značke ostaju poravnati u svojim redovima
  - panel doktora i postojeći DANAS paneli staju na 1536 x 760 bez preklapanja
  - skrivanje panela bez doktora ostaje nepromijenjeno
verification:
  - pytest tests/test_gui/test_main_window.py -q
  - ruff check desktop/views/main_window.py tests/test_gui/test_main_window.py
```

## Scope

Promjena jedne UI konstante sa 48 na 56 px, preciziranje testa i vizuelni
smoke test postojećeg glavnog prozora.

## Out of scope

Promjena širine sidebara, badge semantike, fotografija, podataka i drugih
dashboard panela.
