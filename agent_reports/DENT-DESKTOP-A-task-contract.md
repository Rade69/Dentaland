---
task_id: DENT-DESKTOP-A
risk: MEDIUM
implementer: pi
reviewer: claude
status: REVIEWED PASS — čeka human approval prije merge-a; vidi agent_reports/2026-08-19-DENT-DESKTOP-A-service-edit-status.md za pun izvještaj i review
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-A

```yaml
id: DENT-DESKTOP-A
title: "Faza A — Service capabilities za edit i statuse (desktop scheduler redizajn)"
risk: MEDIUM
objective: >
  Prva od 6 nezavisnih faza redizajna desktop scheduler UX-a (vidi
  docs/dentaland-desktop-fazni-implementacioni-plan-v2.md, sekcija "FAZA A").
  Ova faza NE dira GUI — samo priprema servisni sloj koji će kasnije faze
  (B-E) koristiti. Cilj: dodati update(...) za edit postojećeg termina,
  eksplicitne status-metode mark_completed/mark_no_show, i service-layer
  izvor trajanja usluge (da GUI prestane hardkodovati 60 min).

  update(...) mora mijenjati pacijenta, telefon, email, doktora, uslugu,
  napomenu i start/end vrijeme termina. Overlap provjera ide za NOVOG
  doktora, kroz POSTOJEĆI _check_overlap(..., exclude_id=appt_id) —
  taj parametar već postoji (booking.py:392) i move() ga već koristi
  (booking.py:365-366), NE praviti novi/paralelni overlap helper.

  mark_completed/mark_no_show slijede isti obrazac kao postojeći
  mark_arrived/mark_confirmed/cancel (booking.py) — eksplicitne, uske
  metode, ne generički set_status(bilo šta). COMPLETED, NO_SHOW,
  CANCELLED su terminalna stanja u ovom zadatku — restore/reopen iz
  njih NIJE dio ovog zadatka.

  Service duration: dodati stabilan read-model (npr. ServiceOptionDTO
  sa id/naziv/trajanje_min, po mogućnosti buffer_min ako je relevantan)
  da kasnija Faza B (editor dijalog) može predložiti trajanje prema
  izabranoj usluzi umjesto univerzalnih 60 min.
allowed_paths:
  - src/dentaland/services/booking.py
  - src/dentaland/services/__init__.py
  - tests/test_services.py
  - agent_reports/**
forbidden_paths:
  - desktop/**
  - src/dentaland/models.py
  - migrations/**
  - backend/**
  - web/**
  - CLAUDE.md
  - docs/**
acceptance:
  - update(appt_id, ...) mijenja pacijenta/telefon/email/doktora/uslugu/napomenu/start/end i vraća AppointmentDTO.
  - update koristi postojeći _check_overlap(..., exclude_id=appt_id) — termin pri editovanju ne kolidira sam sa sobom (test to eksplicitno dokazuje).
  - update odbija pravi overlap sa DRUGIM aktivnim terminom istog (novog) doktora.
  - update je jedna transakcija (nema djelimičnog upisa ako overlap provjera padne).
  - mark_completed(appt_id): SCHEDULED -> COMPLETED.
  - mark_no_show(appt_id): SCHEDULED -> NO_SHOW.
  - Poziv mark_completed/mark_no_show/update nad nepostojećim ili terminalnim (CANCELLED/COMPLETED/NO_SHOW) terminom baca jasan ValueError, ne tih no-op.
  - Ne postoji generički set_status(...); ne postoji restore/reopen iz terminalnog stanja.
  - Postojeće mark_confirmed/mark_arrived/cancel ostaju funkcionalno netaknuti (postojeći testovi i dalje prolaze).
  - Service-layer izlaže trajanje usluge (npr. ServiceOptionDTO ili ekvivalentan stabilan tuple/dataclass) — GUI (buduće faze) ne mora hardkodovati 60 min.
  - Nula izmjena u desktop/**, models.py, migrations/**.
verification:
  - pytest tests/ -q
  - ruff check src/dentaland tests
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena implementeru (Pi)

- Prije početka: `python scripts/coordination.py status`, zatim claim tačno gornjih `allowed_paths`.
- Referenca za sve UX/produkt odluke (šta GUI faze B-E očekuju od ovog servisnog sloja): `docs/dentaland-desktop-fazni-implementacioni-plan-v2.md`, sekcija "FAZA A" i "0. Zaključane odluke prije implementacije".
- Ovo je faza 1/6 — GUI se NE dira u ovom zadatku, čak i ako se čini zgodno "dok si već tu". Ako se pri implementaciji otkrije da nešto u planu Faze A nije dovoljno (npr. treba i buffer_min a nije jasno definisan), prijaviti kao `OUT_OF_SCOPE_FINDING` ili STATI i pitati — ne proširivati scope tiho.
- Nakon završetka, evidence fajl ide u `agent_reports/` (vidi `agent_reports/README.md` za format), Claude radi review kao Reviewer 1 prije merge-a.
