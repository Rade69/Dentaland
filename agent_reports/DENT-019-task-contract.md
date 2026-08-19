---
task_id: DENT-019
title: "mypy cleanup — main_window.py (poznat baseline, ne novi bug)"
risk: LOW
implementer: pi
reviewers: [claude]
status: ASSIGNED
created_at: 2026-08-19
---

# Task Contract — DENT-019: mypy cleanup u `desktop/views/main_window.py`

Isti tip probnog taska kao DENT-018 (drugi krug validacije `.agent/`
sloja, sada merge-ovanog u `main`), na drugom fajlu — nema kolizije sa
DENT-018 (Crush).

```yaml
id: DENT-019
title: mypy cleanup — main_window.py
risk: LOW
objective: >
  Ukloniti 2 postojeće mypy greške u desktop/views/main_window.py bez
  promjene ponašanja. Čist type-annotation cleanup.
allowed_paths: [desktop/views/main_window.py, agent_reports/DENT-019-task-contract.md, agent_reports/2026-08-19-DENT-019-*.md]
forbidden_paths: [desktop/views/week_view.py, desktop/views/day_view.py, desktop/views/dialogs/, src/, backend/, web/, migrations/, CLAUDE.md, AGENTS.md, .agent/]
objective_detalji: >
  Tačne greške (potvrđeno svježim `mypy` pokretanjem 19.8.2026):

  1. Linija 52 — nedostaje type annotation na parametru(ima) funkcije.
  2. Linija 540 — nedostaje type annotation na parametru(ima) funkcije.

  Za oba: pogledati kako se parametar koristi u tijelu funkcije i kod
  pozivaoca da se odredi tačan tip — ne stavljati `Any` bez razloga.
acceptance:
  - "mypy desktop/views/main_window.py" vraća 0 grešaka.
  - "mypy desktop backend src/dentaland" i dalje ima tačno 3 preostale
    greške (week_view.py — to je DENT-018, ne ovaj task, dok se oba ne
    merge-uju).
  - Nijedan postojeći GUI test ne padne (tests/test_gui/test_main_window.py
    i drugi testovi koji uvoze main_window).
  - ruff check desktop/views/main_window.py čist.
verification: [mypy desktop/views/main_window.py, pytest tests/test_gui/test_main_window.py -q, ruff check desktop/views/main_window.py]
review:
  reviewers: 1
  required: [scope, ne mijenja ponašanje]
```

## Probni protokol (kao prošli krug)

Prije prve izmjene, pročitaj `.agent/PROJECT_MAP.md` i
`.agent/TASK_ROUTING.md` ("Bug task" sekcija) — sada dostupni direktno u
`main`. U svoj `agent_report` zapiši isti probni signal kao prošli put
(fajlova pročitano prije 1. izmjene, koristio `.agent/`?, pitao za
pojašnjenje?, prekršio scope?) i popuni novi red u
`.agent/TASK_ROUTING.md` tabeli.
