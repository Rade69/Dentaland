---
task_id: DENT-018
title: "mypy cleanup — week_view.py (poznat baseline, ne novi bug)"
risk: LOW
implementer: crush
reviewers: [claude]
status: ASSIGNED
created_at: 2026-08-19
---

# Task Contract — DENT-018: mypy cleanup u `desktop/views/week_view.py`

Ovo je probni task (drugi krug) za validaciju `.agent/` navigacionog sloja,
sada kad je sloj konačno merge-ovan u `main` (prvi krug je otkrio da nije
bio dostupan — vidi `.agent/TASK_ROUTING.md` validacionu tabelu). Ujedno
je i stvaran, mali, dobro-ograničen bug-fix zadatak — testira `prime-bug`
skill (reprodukcija poznatog problema prije popravke), ne `prime-feature`
kao prošli krug.

```yaml
id: DENT-018
title: mypy cleanup — week_view.py
risk: LOW
objective: >
  Ukloniti 3 postojeće mypy greške u desktop/views/week_view.py bez
  promjene ponašanja. Ovo je čist type-annotation cleanup, ne funkcionalna
  izmjena.
allowed_paths: [desktop/views/week_view.py, agent_reports/DENT-018-task-contract.md, agent_reports/2026-08-19-DENT-018-*.md]
forbidden_paths: [desktop/views/main_window.py, desktop/views/day_view.py, desktop/views/dialogs/, src/, backend/, web/, migrations/, CLAUDE.md, AGENTS.md, .agent/]
objective_detalji: >
  Tačne greške (potvrđeno svježim `mypy` pokretanjem 19.8.2026):

  1. Linija 108 — `def __init__(self, store, week_start: date, parent=None):`
     nedostaju tipovi za `store` i `parent`. Dodati odgovarajuće tipove
     (pogledati kako se `store`/`parent` koriste u ostatku klase i u
     pozivaocima da se odredi tačan tip — ne stavljati `Any` bez razloga).
  2. Linija 149 — `"type[QTableWidget]" has no attribute "DragDrop"` —
     PySide6 stub gap, ne stvaran bug (potvrđeno u prethodnoj probi).
     Rješenje: `# type: ignore[attr-defined]` na toj liniji uz kratak
     komentar zašto (stub gap, ne greška u našem kodu), ne zaobilazno
     mijenjanje logike.
  3. Linije 493, 503 — nedostaju type annotation na parametrima. Dodati
     tačne tipove analogno drugim metodama u istoj klasi.
acceptance:
  - "mypy desktop/views/week_view.py" vraća 0 grešaka.
  - "mypy desktop backend src/dentaland" i dalje ima tačno 2 preostale
    greške (main_window.py — to je DENT-019, ne ovaj task).
  - Nijedan postojeći GUI test ne padne (tests/test_gui/test_week_view.py,
    test_week_view_combined.py) — anotacije ne smiju promijeniti runtime
    ponašanje.
  - ruff check desktop/views/week_view.py čist.
verification: [mypy desktop/views/week_view.py, pytest tests/test_gui/test_week_view.py tests/test_gui/test_week_view_combined.py -q, ruff check desktop/views/week_view.py]
review:
  reviewers: 1
  required: [scope, ne mijenja ponašanje]
```

## Probni protokol (kao prošli krug)

Prije prve izmjene, pročitaj `.agent/PROJECT_MAP.md` i
`.agent/TASK_ROUTING.md` ("Bug task" sekcija) — SADA su dostupni direktno
u `main` (`git worktree add ... main` će ih ovaj put nositi). U svoj
`agent_report` zapiši isti probni signal kao prošli put (fajlova
pročitano prije 1. izmjene, koristio `.agent/`?, pitao za pojašnjenje?,
prekršio scope?) i popuni novi red u `.agent/TASK_ROUTING.md` tabeli.
