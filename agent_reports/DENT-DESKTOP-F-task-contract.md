---
task_id: DENT-DESKTOP-F
risk: HIGH
implementer: claude
reviewers: [crush, pi]
status: "MERGED → INTEGRATION_VERIFIED → DONE (merge 1e3c6c0). Human approval: Radovan. Post-merge gate na main: pytest 219 passed, ruff clean, mypy clean (0 issues, 30 fajlova)."
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-F: Hard delete termina

Plan prije implementacije: `agent_reports/2026-08-19-DENT-DESKTOP-F-plan.md`
(Cilj/Pogođeno/Plan/Šta NE dirati/Verifikacija/Rollback/Odbačene opcije,
uključujući FK/cascade provjeru urađenu PRIJE koda).

Odluka Radovana (19.8.2026, AskUserQuestion): "Izbriši termin" je dostupno
za SVE statuse termina, uključujući terminalne (Završen/Nije došao/Otkazan)
— ne samo za aktivne zakazane termine.

```yaml
id: DENT-DESKTOP-F
title: "Faza F — Hard delete termina (HIGH)"
risk: HIGH
objective: >
  Omogućiti trajno, nepovratno brisanje termina — isključivo za greškom
  kreiran zapis. Odvojeno od cancel() (Faza C), koji ostavlja zapis u
  istoriji. Dostupno za sve statuse termina (Radovanova odluka).
allowed_paths:
  - src/dentaland/services/booking.py
  - desktop/views/dialogs/delete_appointment.py
  - desktop/views/dialogs/__init__.py
  - desktop/views/dialogs/appointment_details.py
  - desktop/views/week_view.py
  - desktop/views/day_view.py
  - desktop/views/main_window.py
  - tests/test_services.py
  - tests/test_gui/**
  - agent_reports/**
forbidden_paths:
  - src/dentaland/models.py
  - migrations/**
  - backend/**
  - web/**
  - CLAUDE.md
  - docs/**
  - desktop/views/requests_panel.py
  - desktop/views/sidebar.py
  - desktop/views/dialogs/appointment_editor.py
  - desktop/views/dialogs/move_appointment.py
  - desktop/views/dialogs/cancel_appointment.py
  - desktop/views/dialogs/process_request.py
  - desktop/views/dialogs/base_dialog.py
acceptance:
  - "AppointmentService.delete(appt_id) trajno uklanja tačno jedan red; nepostojeći ID baca ValueError; drugi termini ostaju netaknuti."
  - "delete() radi za BILO KOJI status termina (uključujući terminalne) — nema status-provjere kao kod cancel()/mark_*."
  - "FK/cascade provjera urađena i dokumentovana PRIJE koda (u plan fajlu) — potvrđeno da appointments.id nije referenciran ni od jedne druge tabele."
  - "DeleteAppointmentDialog: full red primary button, NIJE default (autoDefault=False, isDefault=False) — Enter ga ne aktivira."
  - "\"Izbriši termin\" u Detalji termina je vizuelno odvojeno (razmak, poseban stil) ispod uslovnih/operativnih akcija, i vidljivo i za terminalne termine (gdje su sve OSTALE akcije skrivene)."
  - "\"Izbriši termin\" u context meniju (WeekView i DayView) je iza posebnog separatora na dnu, dostupno bez obzira na status."
  - "cancel() i delete() imaju jasno različite rezultate (cancel: status=CANCELLED, zapis ostaje; delete: red nestaje iz baze) — pokriveno testom."
  - "Nula izmjena u models.py/migrations — nema šematske promjene."
  - "Nula izmjena van allowed_paths."
verification:
  - pytest tests/ -q
  - ruff check src/dentaland desktop tests
  - "mypy src/dentaland desktop backend   # mora ostati 6 grešaka (baseline)"
review:
  reviewers: 2
  required: [security, architecture, scope, data-safety]
```

## Napomena za Crush i Pi (Reviewer 1/2)

Implementirao je Claude direktno (HIGH-risk pravilo iz `CLAUDE.md`). Vi ste
nezavisni reviewer-i — Claude se ne vraća da sam sebe pregleda u istom
kontekstu. Pun kontekst:

- Plan fajl (FK provjera, odbačene opcije, rollback): `agent_reports/2026-08-19-DENT-DESKTOP-F-plan.md`
- Implementer izvještaj: `agent_reports/2026-08-19-DENT-DESKTOP-F-hard-delete.md`
- Worktree: `Dentaland-worktrees/DENT-DESKTOP-F-hard-delete`, grana `task/DENT-DESKTOP-F-hard-delete`
- Naročito provjerite: (1) da `delete()` stvarno nema cascade posljedice — ne vjerovati samo mojoj statičkoj FK analizi, provjerite i sami u `models.py`; (2) da Enter stvarno ne aktivira brisanje (autoDefault/isDefault na dugmetu); (3) da je odluka "dostupno za sve statuse" ispravno implementirana svuda (Detalji, oba context menija).

Nakon oba reviewa, Radovan daje human approval prije merge-a (HIGH tok:
Implementer → verifikacija → Reviewer 1 → Reviewer 2 → human approval → merge).
