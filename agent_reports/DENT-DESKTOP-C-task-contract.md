---
task_id: DENT-DESKTOP-C
risk: MEDIUM
implementer: pi
reviewer: radovan (Reviewer 1)
status: REVIEWED PASS_WITH_NOTES — čeka human approval; vidi agent_reports/2026-08-19-DENT-DESKTOP-C-detalji-akcije.md
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-C: Detalji + klik/context menu + pomjeranje/otkazivanje

Porijeklo: `docs/redizajn/dentaland-desktop-fazni-implementacioni-plan-v2.md`,
**FAZA C**. Zavisnosti: A + B (oba merge-ovana). Hard delete NIJE dio ove faze.

```yaml
id: DENT-DESKTOP-C
title: Detalji termina + klik/context menu + pomjeranje/otkazivanje (Faza C redizajna)
risk: MEDIUM
objective: >
  Napraviti jasan operativni model rada sa postojećim terminom: lijevi klik
  otvara "Detalji termina", desni klik daje status-aware brze akcije, drag&drop
  ostaje kao brzo pomjeranje, a pomjeranje i otkazivanje dobijaju stilizovane
  modalne dijaloge. WeekView postaje "glup" (emituje signale), MainWindow
  orkestrira store pozive i refresh.
allowed_paths:
  - desktop/views/week_view.py
  - desktop/views/main_window.py
  - desktop/views/dialogs/**
  - tests/test_gui/test_week_view.py
  - tests/test_gui/test_main_window.py
  - tests/test_gui/test_appointment_details_dialog.py
  - tests/test_gui/test_destructive_dialogs.py
  - agent_reports/**
forbidden_paths:
  - src/dentaland/**
  - desktop/fake_data.py
  - desktop/views/requests_panel.py
  - desktop/views/sidebar.py
  - desktop/views/appointment_dialog.py
  - desktop/views/dialogs/appointment_editor.py
  - desktop/views/dialogs/base_dialog.py
  - desktop/print_document.py
  - migrations/**
  - backend/**
  - web/**
  - CLAUDE.md
  - AGENTS.md
  - docs/**
acceptance:
  - WeekView emituje appointment_clicked(int) na lijevi klik na termin (prazan slot i dalje slot_selected).
  - WeekView emituje appointment_action_requested(int, str) iz status-aware context menija (ne poziva store direktno).
  - Detalji termina prikazuju ime/telefon/email/datum/vrijeme/trajanje/doktora/uslugu/napomenu/trenutno stanje.
  - Status NIJE dropdown — badge + uslovne akcije (Potvrdi/Stigao/Završen/"nije došao").
  - Terminalni statusi (COMPLETED/NO_SHOW/CANCELLED) nemaju povratne statusne akcije.
  - Operativne akcije: Uredi termin (reuse _edit_appointment iz Faze B), Pomjeri termin (move), Otkaži termin (cancel).
  - Pomjeri termin čuva trajanje; overlap greška je inline i modal ostaje otvoren.
  - Otkaži termin ne traži razlog; zapis ostaje u istoriji (cancel, ne delete).
  - Hard delete NE postoji.
  - Statusni summary se osvježava nakon svake akcije.
  - Nula SQLAlchemy importa u desktop/views/.
verification:
  - pytest tests/test_gui/test_week_view.py tests/test_gui/test_main_window.py tests/test_gui/test_appointment_details_dialog.py tests/test_gui/test_destructive_dialogs.py -v
  - pytest tests/ -q
  - ruff check desktop tests
  - mypy src/dentaland desktop backend
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena

- Postojeći `unmark_arrived` (poništi slučajno "Stigao") se ZADRŽAVA kao "Poništi
  (nije stiglo)" akcija kad je termin već označen kao stigao — ne regresira se
  nedavno dodati feature.
- `appointment_dialog.py`, `dialogs/appointment_editor.py` i `base_dialog.py` su
  forbidden ovdje — Faza B ih je dostavila, ne diraju se.
