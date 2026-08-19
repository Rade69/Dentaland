---
task_id: DENT-DESKTOP-B3
risk: LOW
implementer: pi
reviewer: claude
status: REVIEWED PASS_WITH_NOTES — čeka human approval; vidi agent_reports/2026-08-19-DENT-DESKTOP-B3-ikonice.md
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-B3: ikonica u zaglavlju dijaloga + prozorska ikonica

Radovan je uočio uživo (screenshot "Detalji termina") dvije odvojene
stvari:

1. Modal header (sadržaj unutar dijaloga) ima samo tekst naslova, bez
   ikonice — originalni mokapi su za svaki dijalog imali malu ikonicu u
   krugu odmah lijevo od naslova.
2. Naslovna traka PROZORA (OS nivo, iznad sadržaja) prikazuje generički
   Qt/Windows simbol — provjereno u kodu: `setWindowIcon()` se NIGDJE
   ne poziva, ni na `MainWindow` ni na ijednom dijalogu, pa OS prikazuje
   default placeholder umjesto Dentaland loga (`web/assets/logo.png`,
   isti fajl koji `sidebar.py` već koristi za logo u sidebar-u).

```yaml
id: DENT-DESKTOP-B3
title: "Ikonica u zaglavlju dijaloga + prozorska ikonica (window icon)"
risk: LOW
objective: >
  DIO 1 — ikonica u sadržaju dijaloga:
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

  DIO 2 — prozorska ikonica (OS titlebar/taskbar):
  BaseDialog.__init__ poziva self.setWindowIcon(QIcon(str(logo_path)))
  koristeći isti `web/assets/logo.png` put kao sidebar.py (računat
  relativno od fajla, isti Path(__file__).resolve().parents[N] obrazac
  — provjeriti tačan broj .parents[] koraka od
  desktop/views/dialogs/base_dialog.py do repo korijena, NIJE isti broj
  kao u sidebar.py jer je dialogs/ jedan nivo dublje). Ovo automatski
  pokriva SVE dijaloge odjednom (jedna izmjena u BaseDialog-u).

  main_window.py TAKOĐE treba self.setWindowIcon(...) sa istim logom —
  to je glavni prozor/taskbar ikonica aplikacije, van BaseDialog
  nasljeđivanja. Ovo je JEDINA dozvoljena izmjena u main_window.py u
  ovom zadatku — samo dodavanje setWindowIcon poziva, ništa drugo.

  Čisto vizuelni zadatak — get_data()/selected_action()/validate()/values()
  potpisi i ponašanje se NE mijenjaju.
allowed_paths:
  - desktop/views/dialogs/base_dialog.py
  - desktop/views/dialogs/appointment_editor.py
  - desktop/views/dialogs/appointment_details.py
  - desktop/views/dialogs/move_appointment.py
  - desktop/views/dialogs/cancel_appointment.py
  - desktop/views/dialogs/process_request.py
  - desktop/views/main_window.py   # ISKLJUČIVO setWindowIcon() poziv, ništa drugo
  - agent_reports/**
forbidden_paths:
  - src/dentaland/**
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
  - Svaki dijalog (kroz BaseDialog) i MainWindow imaju setWindowIcon() postavljen na Dentaland logo (web/assets/logo.png) — provjeriti da putanja stvarno postoji sa mjesta odakle se računa (ne pretpostaviti broj .parents[] koraka, testirati).
  - get_data()/selected_action()/validate()/values() nepromijenjeni — postojeći testovi prolaze bez izmjena logike (mogu se dodati novi testovi za ikonicu, ali stari se ne smiju pokvariti).
  - Nula izmjena u main_window.py van setWindowIcon poziva.
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
