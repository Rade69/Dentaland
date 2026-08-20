---
task_id: DENT-020
title: "Scheduler za email podsjetnike (bez schema izmjene)"
risk: MEDIUM
implementer: codex
reviewers: [claude]
status: ASSIGNED
created_at: 2026-08-20
---

# Task Contract — DENT-020: Scheduler za email podsjetnike

**Namjerno odstupanje od Uloge tabele (dokumentovano, ne tiho):** po
`docs/dentaland-agentski-razvoj.md`, Codex je predviđen kao opcion
Implementer na LOW/MEDIUM **frontend/GUI** poslu — ovaj zadatak je
backend/servisni (scheduler), van te uže kategorije. Radovan je eksplicitno
tražio da ovaj konkretan zadatak ide Codex-u, radi testiranja da li
`.agent/` navigacioni sloj pomaže Codex-u kao Implementer-u (dosadašnja tri
review kruga nisu to izmjerila — vidi `.agent/TASK_ROUTING.md` validacionu
tabelu, četvrti red).

```yaml
id: DENT-020
title: Scheduler za email podsjetnike
risk: MEDIUM
objective: >
  send_appointment_reminder() (DENT-017, src/dentaland/services/notifications.py)
  postoji ali ništa je trenutno ne poziva. Dodati periodičan in-process
  mehanizam koji šalje podsjetnik za termine u uskom vremenskom prozoru
  prije termina (predloženo: "sutra u ovo doba" — tačan prozor je tvoja
  tehnička odluka, obrazloži izbor u izvještaju).
allowed_paths: [backend/, src/dentaland/services/notifications.py, pyproject.toml, tests/test_backend.py, tests/test_notifications.py, agent_reports/DENT-020-task-contract.md, agent_reports/2026-08-20-DENT-020-*.md]
forbidden_paths: [src/dentaland/models.py, migrations/, desktop/, web/, src/dentaland/services/booking.py, src/dentaland/services/requests.py, CLAUDE.md, AGENTS.md, docs/dentaland-agentski-razvoj.md, .agent/]
objective_detalji: >
  ODLUKA (Radovan, 20.8.2026): BEZ schema izmjene za sada. Appointment
  model nema polje za praćenje "podsjetnik već poslan" — dodavanje takvog
  polja bi bila migracija (HIGH risk, van obima ovog MEDIUM zadatka).
  Prihvaćen rizik: ako se job slučajno pokrene dvaput (npr. restart
  servera), pacijent može dobiti dva podsjetnika za isti termin — rijedak,
  neopasan edge-case, ne blokira ovaj pristup.

  Tehnička odluka (tvoja, nije propisano): in-process periodičan mehanizam
  bez dodatne eksterne infrastrukture (u duhu CLAUDE.md "jedan VPS, jedna
  instanca" — ne uvoditi Redis/Celery/eksterni cron/message broker). Bilo
  APScheduler (nije još zavisnost, možeš dodati u pyproject.toml ako
  odabereš) bilo jednostavan asyncio background task pri FastAPI startup-u
  — obrazloži izbor.

  Koristi POSTOJEĆU send_appointment_reminder(to_email, start_time) iz
  notifications.py — ne piši novu logiku slanja, samo mehanizam koji je
  poziva u pravom trenutku za prave termine.
acceptance:
  - Periodičan mehanizam postoji i pokreće se bez ručne intervencije nakon starta backend-a.
  - Šalje podsjetnik SAMO za termine u definisanom uskom prozoru (ne za sve buduće SCHEDULED termine).
  - Koristi postojeću send_appointment_reminder(), ne duplira slanje logiku.
  - Nema izmjene models.py ni nove migracije.
  - Test dokazuje da mehanizam bira ispravne termine (mockuj "trenutno vrijeme", ne čekaj stvarne sate) i da NE bira termine van prozora.
  - Nula regresije u postojećim testovima.
verification: [pytest tests/ -q, ruff check backend src/dentaland tests, mypy backend src/dentaland]
review:
  reviewers: 1
  required: [architecture, scope, "da li je duplo-slanje rizik jasno dokumentovan u kodu/komentaru"]
```
