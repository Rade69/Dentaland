---
task_id: DENT-DESKTOP-B3
risk: LOW
implementer: pi
reviewer: claude
status: PENDING
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-B3: ikonica u zaglavlju dijaloga

Radovan je uočio uživo (screenshot "Detalji termina") da modal header
ima samo tekst naslova, bez ikonice — originalni mokapi (na početku
redizajna) su za svaki dijalog imali malu ikonicu u krugu odmah lijevo
od naslova (npr. kalendar za Detalji/Editor/Obradi, upozoravajuća
ikonica za Otkaži). Trenutno `BaseDialog` gradi header kao samo
`QLabel(title)`, bez ikonice.

```yaml
id: DENT-DESKTOP-B3
title: "Ikonica u zaglavlju dijaloga (BaseDialog header)"
risk: LOW
objective: >
  Dodati malu ikonicu (isti krug/stil kao make_icon_label, veličina malo
  veća — npr. 20px umjesto 16px za bolju vidljivost u headeru) lijevo od
  naslova u BaseDialog headeru. BaseDialog.__init__ dobija novi parametar
  icon: str = "calendar" (default kalendar, jer većina dijaloga jeste
  scheduling-vezana). Header layout postaje QHBoxLayout(icon_label,
  title_label) umjesto samog title_label-a.

  Svaki postojeći dijalog eksplicitno prosljeđuje icon parametar:
  - AppointmentEditorDialog -> "calendar"
  - AppointmentDetailsDialog -> "calendar"
  - MoveAppointmentDialog -> "clock"
  - CancelAppointmentDialog -> "alert"
  - ProcessRequestDialog -> "calendar"

  Čisto vizuelni zadatak — get_data()/selected_action()/validate()/values()
  potpisi i ponašanje se NE mijenjaju. Ni main_window.py ni requests_panel.py
  se ne diraju (samo pozivaju konstruktore dijaloga koji već imaju default
  vrijednost za icon, pa postojeći pozivi rade bez izmjene ako se ne doda
  eksplicitni icon= wiring tamo).
allowed_paths:
  - desktop/views/dialogs/base_dialog.py
  - desktop/views/dialogs/appointment_editor.py
  - desktop/views/dialogs/appointment_details.py
  - desktop/views/dialogs/move_appointment.py
  - desktop/views/dialogs/cancel_appointment.py
  - desktop/views/dialogs/process_request.py
  - agent_reports/**
forbidden_paths:
  - src/dentaland/**
  - desktop/views/main_window.py
  - desktop/views/week_view.py
  - desktop/views/day_view.py
  - desktop/views/requests_panel.py
  - desktop/views/sidebar.py
  - migrations/**
  - backend/**
  - web/**
  - CLAUDE.md
  - docs/**
acceptance:
  - BaseDialog header prikazuje malu ikonicu u krugu lijevo od naslova, za sve dijaloge.
  - Svaki dijalog koristi tematski odgovarajuću ikonicu (vidi mapiranje gore).
  - get_data()/selected_action()/validate()/values() nepromijenjeni — postojeći testovi prolaze bez izmjena logike (mogu se dodati novi testovi za ikonicu, ali stari se ne smiju pokvariti).
  - Nula izmjena van allowed_paths.
verification:
  - pytest tests/ -q
  - ruff check desktop tests
  - mypy src/dentaland desktop backend   # mora ostati 6 grešaka (baseline)
review:
  reviewers: 1
  required: [visual-fidelity, scope]
```

## Napomena

LOW risk, minimalna ceremonija — jedan reviewer (Claude), human approval
opcion po LOW toku iz CLAUDE.md, ali ide ipak kroz mene za review prije
merge-a kao i ostale GUI faze ovog redizajna, radi konzistentnosti.
