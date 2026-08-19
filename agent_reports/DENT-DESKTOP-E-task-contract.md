---
task_id: DENT-DESKTOP-E
risk: MEDIUM
implementer: pi
reviewer: radovan (Reviewer 1)
status: REVIEWED PASS — čeka human approval; vidi agent_reports/2026-08-19-DENT-DESKTOP-E-dan-sedmica.md
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-E: Dan/Sedmica + scheduler cleanup

Porijeklo: `docs/redizajn/dentaland-desktop-fazni-implementacioni-plan-v2.md`,
**FAZA E**. Zavisnost: C. Cilj: dva jasna scheduler prikaza (Dan + Sedmica) bez
trećeg nejasnog moda i bez miješanja sa statusnim summaryjem.

```yaml
id: DENT-DESKTOP-E
title: Dan/Sedmica prikazi + scheduler cleanup (Faza E redizajna)
risk: MEDIUM
objective: >
  Implementirati DayView (doktori kao kolone, vrijeme vertikalno, izabrani datum,
  isti appointment-card mentalni model i click/context ponašanje kao WeekView),
  omogućiti "Dan" dugme (prebacivanje Dan/Sedmica), ukloniti "Po doktoru/Paralelno"
  kao redundantni treći mod, i sačuvati statusni summary za oba prikaza.
allowed_paths:
  - desktop/views/main_window.py
  - desktop/views/week_view.py
  - desktop/views/day_view.py
  - desktop/views/widgets/**
  - tests/test_gui/test_main_window.py
  - tests/test_gui/test_week_view.py
  - tests/test_gui/test_day_view.py
  - agent_reports/**
forbidden_paths:
  - src/dentaland/**
  - desktop/fake_data.py
  - desktop/views/dialogs/**
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
  - DayView prikazuje doktore kao kolone i vrijeme vertikalno (izabrani datum).
  - "Dan" dugme je omogućeno i prebacuje Dan/Sedmica prikaz.
  - WeekView (Sedmica) funkcionalno ne regresira (filter doktora, click/context/drag).
  - "Po doktoru"/"Paralelno" su uklonjeni (nema trećeg nejasnog moda).
  - Statusni summary OSTAIE i radi za oba prikaza.
  - DayView emituje appointment_clicked i appointment_action_requested (isti details/context tok).
  - Nula izmjena u src/dentaland/**, dialogs/**, requests_panel.py, sidebar.py.
verification:
  - pytest tests/test_gui/test_day_view.py tests/test_gui/test_main_window.py tests/test_gui/test_week_view.py -v
  - pytest tests/ -q
  - ruff check desktop tests
  - mypy src/dentaland desktop backend
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena

- DayView je ZASEBAN widget (ne mega-WeekView) — dijeli samo male stabilne
  helpere iz week_view (STATUS_META/_status_key/_DOCTOR_PALETTE/_DOCTOR_CARD_PALETTE).
- Drag&drop ostaje WeekView-specific (promjena vremena); DayView pokriva click
  (details) i context menu (brze akcije) — doktor se mijenja kroz "Uredi".
- `week_view.py` se dira samo ako zatreba izdvajanje dijeljenih helfera.
