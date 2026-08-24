---
task_id: DENT-022
risk: HIGH
implementer: claude
reviewers: [codex, crush-or-pi]
status: "IMPLEMENTED — čeka nezavisan review (Codex obavezan Reviewer 1, Crush ili Pi Reviewer 2), zatim human approval."
created_at: 2026-08-23
---

# Task Contract — DENT-022: zaštita od dupliranog slanja email podsjetnika

Plan prije implementacije: `agent_reports/2026-08-23-DENT-022-plan.md`
(Cilj/Pogođeno/Plan/Šta NE dirati/Plan verifikacije/Rollback/Odbačene
opcije, uključujući analizu stvarnog mehanizma duplikata urađenu PRIJE
koda — pušovano na `main` kao commit `d1a3330` prije nego što je
worktree otvoren).

Kontekst: `docs/dentaland-desktop-korektivni-plan.md` nije izvor ovog
taska — ovo je odgovor na Radovanov zahtjev ("Riješi greške") nakon
audita email funkcionalnosti, koji je otkrio dvije poznate praznine
(ova je jedna od njih; druga, SMTP dokumentacija, je LOW risk i ide
odvojeno).

```yaml
id: DENT-022
title: "Zaštita od dupliranog slanja email podsjetnika (HIGH)"
risk: HIGH
objective: >
  Spriječiti da isti termin dobije podsjetnik dva puta nakon restarta
  backend procesa ili slučajnog dvostrukog pokretanja scheduler-a —
  eksplicitno prihvaćen rizik iz DENT-020 Task Contracta, sad zatvoren
  aditivnom nullable kolonom (isti obrazac kao confirmed_at/arrived_at
  iz DENT-012).
allowed_paths:
  - src/dentaland/models.py
  - migrations/versions/d4e5f6a7b8c9_reminder_sent_at.py
  - src/dentaland/services/notifications.py
  - tests/test_backend.py
  - agent_reports/**
forbidden_paths:
  - desktop/
  - web/
  - backend/main.py
  - backend/reminder_scheduler.py
  - src/dentaland/services/booking.py
  - src/dentaland/services/requests.py
acceptance:
  - "Appointment.reminder_sent_at je nova nullable kolona (TZDateTime), NULL = podsjetnik nije poslan."
  - "Migracija d4e5f6a7b8c9 je aditivna, upgrade/downgrade simetričan (provjereno ručno na pravoj SQLite bazi, ne samo test suite)."
  - "send_due_appointment_reminders() filtrira reminder_sent_at IS NULL i postavlja ga nakon best-effort slanja u ISTOJ sesiji/transakciji."
  - "Isti termin obrađen u dva preklapajuća/uzastopna poziva (simulacija restarta) šalje SAMO JEDNOM — pokriveno novim testom."
  - "Postojeći scheduler testovi (prozor, naivno vrijeme, startup wiring) ne regresiraju."
  - "Nula izmjena u desktop/web/main_window/reminder_scheduler.py — dedup je isključivo u servisnom sloju."
verification:
  - pytest tests/ -q
  - ruff check src/dentaland desktop backend tests
  - "mypy src/dentaland desktop backend"
  - "alembic upgrade head / downgrade -1 / upgrade head na pravoj SQLite bazi — ručno potvrđeno simetrično"
review:
  reviewers: 2
  required: [security, architecture, data-safety, migration-safety]
```

## Napomena za Codex i Crush/Pi (Reviewer 1/2)

Implementirao je Claude direktno (HIGH-risk pravilo iz `CLAUDE.md`). Vi
ste nezavisni reviewer-i — Claude se ne vraća da sam sebe pregleda u
istom kontekstu. Pun kontekst:

- Plan fajl (analiza stvarnog mehanizma duplikata, odbačene opcije):
  `agent_reports/2026-08-23-DENT-022-plan.md`
- Implementer izvještaj: `agent_reports/2026-08-23-DENT-022-reminder-dedup.md`
- Worktree: `Dentaland-worktrees/DENT-022-reminder-dedup`, grana
  `task/DENT-022-reminder-dedup`
- Naročito provjerite: (1) da migracija stvarno ne gubi postojeće
  podatke (postojeći `test_migracija_cuva_postojece_termine_pri_upgrade_i_downgrade`
  pokriva OPŠTI slučaj — provjerite da i dalje prolazi sa novom
  kolonom); (2) da `reminder_sent_at` postavljanje i `send_appointment_reminder`
  poziv dijele istu sesiju/transakciju (nema race-a između fetch i
  update); (3) da dedup test stvarno hvata regresiju — po mogućnosti
  privremeno uklonite filter/update i potvrdite da test PADA prije nego
  vjerujete da prolazi ispravno.

Nakon oba reviewa, Radovan daje human approval prije merge-a (HIGH tok:
Implementer → verifikacija → Reviewer 1 → Reviewer 2 → human approval →
merge).
