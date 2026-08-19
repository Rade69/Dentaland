---
task_id: DENT-DESKTOP-D
risk: MEDIUM
implementer: pi
reviewer: radovan (Reviewer 1)
status: REVIEWED PASS — čeka human approval; vidi agent_reports/2026-08-19-DENT-DESKTOP-D-online-zahtjevi.md
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-D: Online zahtjevi + desni operativni panel

Porijeklo: `docs/redizajn/dentaland-desktop-fazni-implementacioni-plan-v2.md`,
**FAZA D**. Zavisnost: B (+ B2 vizuelni polish). Cilj: zamijeniti generički
`ConfirmationDialog` i pojednostaviti desni panel.

```yaml
id: DENT-DESKTOP-D
title: Online zahtjevi + desni operativni panel (Faza D redizajna)
risk: MEDIUM
objective: >
  Zamijeniti generički ConfirmationDialog stilizovanim ProcessRequestDialog
  (BaseDialog + B2 helperi), svesti pending karticu na jednu primarnu akciju
  "Obradi", i ukloniti izmišljeni "Sljedeći slobodan termin" placeholder.
  Vrijeme se bira QTimeEdit-om (ručno) — bez lažnih slot dugmadi.
allowed_paths:
  - desktop/views/requests_panel.py
  - desktop/views/dialogs/**
  - desktop/views/main_window.py  # samo wiring ako zatreba
  - tests/test_gui/test_requests_panel.py
  - tests/test_gui/test_process_request_dialog.py
  - agent_reports/**
forbidden_paths:
  - src/dentaland/**
  - desktop/fake_data.py
  - desktop/views/week_view.py
  - desktop/views/sidebar.py
  - desktop/views/appointment_dialog.py
  - migrations/**
  - backend/**
  - web/**
  - CLAUDE.md
  - AGENTS.md
  - docs/**
acceptance:
  - Pending kartica ima JEDNO primarno dugme "Obradi" (nema "Potvrdi | Odbij" par na kartici).
  - ProcessRequestDialog je BaseDialog-based i koristi B2 helpere (make_icon_label, add_outline_button/footer).
  - ProcessRequestDialog prikazuje read-only: pacijent, telefon, email (ako postoji), željeni datum.
  - ProcessRequestDialog input: doktor (combo), vrijeme (QTimeEdit — NE lažni slot dugmići), usluga (combo).
  - Footer: [Odbij zahtjev] [Potvrdi termin]; reject poziva reject_pending, confirm poziva confirm_pending.
  - Generički ConfirmationDialog je uklonjen iz glavnog toka.
  - "Sljedeći slobodan termin" placeholder je uklonjen.
  - Nula izmjena u src/dentaland/**, week_view.py, sidebar.py.
  - Postojeći testovi prolaze (uz dopune).
verification:
  - pytest tests/test_gui/test_requests_panel.py tests/test_gui/test_process_request_dialog.py -v
  - pytest tests/ -q
  - ruff check desktop tests
  - mypy src/dentaland desktop backend
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena

- "Čekaju potvrdu" (awaiting termini, ne zahtjevi) ZADRŽAVA svoje "Potvrdi"/"Odbaci"
  akcije — plan D.2 mijenja samo pending "request karticu" (zahtjev), ne tu listu.
- `main_window.py` vjerovatno ne treba dirati (DashboardPanels je već ožičen);
  dira se samo ako wiring zatreba.
