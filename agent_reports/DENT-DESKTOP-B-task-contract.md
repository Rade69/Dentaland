---
task_id: DENT-DESKTOP-B
risk: MEDIUM
implementer: pi
reviewer: radovan (Reviewer 1)
status: REVIEWED PASS — čeka human approval; vidi agent_reports/2026-08-19-DENT-DESKTOP-B-unified-editor.md
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-B: Unified Novi/Uredi termin editor

Porijeklo: `docs/redizajn/dentaland-desktop-fazni-implementacioni-plan-v2.md`,
**FAZA B** (Vizuelni sistem modala + Unified Novi/Uredi termin). Zavisnost:
Faza A (merge-ovana). Ovo je prva GUI faza redizajna — servisni sloj se ne
mijenja.

```yaml
id: DENT-DESKTOP-B
title: Vizuelni sistem modala + Unified Novi/Uredi termin editor (Faza B redizajna)
risk: MEDIUM
objective: >
  Ukloniti generički create workflow (QInputDialog za doktora + AppointmentDialog
  bez validacije) i napraviti jedan kvalitetan editor (AppointmentEditorDialog)
  na reusable BaseDialog osnovi. Doktor se bira u modalu (ne QInputDialog),
  trajanje dolazi iz service_options() (ne hardkodovanih 60 min), a greške
  (overlap/validacija) se prikazuju inline u modalu.
allowed_paths:
  - desktop/views/appointment_dialog.py
  - desktop/views/main_window.py
  - desktop/views/dialogs/**
  - tests/test_gui/test_appointment_dialog.py
  - tests/test_gui/test_main_window.py
  - agent_reports/**
forbidden_paths:
  - src/dentaland/**
  - desktop/fake_data.py
  - desktop/views/week_view.py
  - desktop/views/requests_panel.py
  - desktop/views/sidebar.py
  - desktop/print_document.py
  - migrations/**
  - backend/**
  - web/**
  - CLAUDE.md
  - AGENTS.md
  - docs/**
acceptance:
  - BaseDialog je reusable vizuelna osnova (white surface, teal primary, radius, custom header/footer, bez generičkog QDialogButtonBox izgleda).
  - AppointmentEditorDialog pokriva i Novi i Uredi termin (jedan unified editor).
  - Polja: Pacijent*, Telefon, Email, Doktor*, Datum*, Vrijeme*, Trajanje*, Usluga*, Napomena.
  - Doktor se bira unutar modala (nema QInputDialog "Koji doktor?" toka).
  - Trajanje se predlaže iz service_options() (trajanje_min), ne univerzalnih 60 min.
  - Edit mode prefilluje postojeći DTO i save koristi update().
  - Inline greške: overlap/validacija se prikazuju u modalu, modal ostaje otvoren.
  - Nula SQLAlchemy importa u desktop/views/.
  - Postojeći scheduler (WeekView) nije funkcionalno regresiran.
verification:
  - pytest tests/test_gui/test_appointment_dialog.py tests/test_gui/test_main_window.py -v
  - pytest tests/ -q
  - ruff check desktop tests
  - mypy src/dentaland
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena

- Edit MODE editora je implementiran ovdje (konstruktor + prefill + save kroz
  `update()`), ali ožičavanje "Uredi termin" dugmeta kroz `Detalji termina` je
  Faza C — ovdje samo priprema.
- `desktop/fake_data.py` NIJE u allowed_paths — editor se piše da radi sa
  plain podacima (liste doktora/usluga), ne sa konkretnim store tipom.
