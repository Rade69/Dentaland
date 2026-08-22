---
task_id: FIX-07
risk: LOW
implementer: codex
reviewers: [independent]
verdict: PENDING
commits: []
created_at: 2026-08-22
---

# Task Contract — WeekView kartica odsječena na donjoj granici

```yaml
id: FIX-07
title: Ne odsijecati sadržaj termina u posljednjem redu WeekView-a
risk: LOW
objective: Termin koji prelazi donju granicu prikaza mora koristiti kompaktan sadržaj koji staje u posljednji vidljivi red.
allowed_paths:
  - desktop/views/week_view.py
  - tests/test_gui/test_week_view.py
  - agent_reports/FIX-07-task-contract.md
  - agent_reports/2026-08-22-FIX-07-weekview-bottom-card.md
forbidden_paths:
  - src/dentaland/
  - migrations/
  - desktop/views/day_view.py
acceptance:
  - termin 19:00–20:30 nije prikazan trorednom karticom odsječenom na 20:00
  - termin zadržava stvarno vrijeme 19:00–20:30 u tekstu kartice
  - termini sa dovoljno vidljivih redova zadržavaju postojeći prošireni prikaz
  - broj redova i granice WeekView-a ostaju nepromijenjeni
verification:
  - pytest tests/test_gui/test_week_view.py -q
  - ruff check desktop/views/week_view.py tests/test_gui/test_week_view.py
```

## Scope

Samo odluka o kompaktnom/proširenom prikazu kartice na osnovu stvarno
dostupnog vizuelnog raspona pri donjoj granici tabele.

## Out of scope

Promjena radnog vremena, broja redova, validacije termina, baze i DayView-a.
