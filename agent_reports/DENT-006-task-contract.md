---
task_id: DENT-006
risk: MEDIUM
implementer: crush
reviewer: claude
status: REVIEWED — vidi 2026-08-16-DENT-006-raspored-svi-doktori.md za pun izvještaj
created_at: 2026-08-16
---

# Task Contract — DENT-006

```yaml
id: DENT-006
title: Faza 0 — Raspored prikazuje sva tri doktora istovremeno, u boji
risk: MEDIUM
objective: >
  Redizajnirati sedmični raspored (WeekView) da prikazuje termine SVA TRI
  doktora istovremeno u istoj mreži, boja-kodirano po doktoru, umjesto
  trenutnog dropdown-a koji filtrira prikaz na jednog doktora. Dodati
  filter tabove iznad rasporeda: "Svi doktori" / "Dr Ljubo" / "Dr Zorka" /
  "Dr Ana" — "Svi doktori" prikazuje sve boja-kodirano, klik na
  pojedinačnog doktora filtrira prikaz na samo njegove termine (zadržava
  postojeće ponašanje kao jednu od opcija, ne gubi funkcionalnost).

  Mokap (dat od Radovana) je referenca za vizuelni pravac — boja po
  doktoru (npr. zelena/crvena/plava), tabovi iznad rasporeda, "Danas" +
  strelice za navigaciju sedmice. NE implementirati iz mokapa: sidebar
  navigaciju (Termini/Pacijenti/Kalendar/Izvještaji/Postavke), panel
  "Novi zahtjevi", "+ Novi termin"/"Štampa" dugmad kao na mokapu (postojeća
  dugmad iz DENT-002 ostaju), "Osoblje/Administrator" identitet, desni
  sidebar (Brzi pregled, mini kalendar). Ovo je namjerno odloženo (dogovoreno
  16.8.2026) — gradi se samo kad stvarno zatreba, ne unaprijed.

  "Novi zahtjevi" panel je EKSPLICITNO VAN OBIMA ovog zadatka — zavisi od
  PENDING statusa i backend rada koji Claude radi paralelno (DENT-007).
  Dolazi kao poseban budući zadatak KAD oba (ovaj redizajn + DENT-007)
  budu gotova, ne sad.
allowed_paths: [desktop/views/main_window.py, desktop/views/week_view.py, src/dentaland/services/booking.py, tests/test_services.py, tests/test_gui/**, agent_reports/**]
forbidden_paths: [src/dentaland/models.py, migrations/**, src/dentaland/services/requests.py, backend/**, web/**, desktop/fake_data.py, desktop/views/appointment_dialog.py, CLAUDE.md, AGENTS.md, docs/**]
acceptance:
  - Raspored prikazuje termine sva tri doktora istovremeno kad je odabrano "Svi doktori", svaki doktor vizuelno razlikovan bojom.
  - Filter tabovi (Svi doktori / po jednom doktoru) rade — klik na pojedinačnog doktora filtrira prikaz na njegove termine.
  - Klik na prazan slot za unos termina i dalje traži koji doktor (ako je "Svi doktori" aktivan) prije nego otvori dijalog — ne smije kreirati termin bez jasnog vlasnika.
  - Drag&drop i dalje radi (čuva trajanje, hvata OverlapError) — ne regresija na DENT-003 rad.
  - `AppointmentService` dobija metodu za dohvat termina SVIH doktora odjednom (npr. `all_combined()`), pošto trenutni `all()` vraća samo za `self.doctor_id`.
  - Nula SQLAlchemy importa u `desktop/views/` (arhitekturno pravilo, i dalje važi).
  - Postojeći testovi (`test_services.py`, `test_gui/`) i dalje prolaze uz nove testove za kombinovani prikaz i filtriranje.
verification:
  - pytest tests/ -q
  - ruff check src/dentaland desktop tests
  - "grep -ri sqlalchemy desktop/views/*.py  # očekivano prazno"
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena

Radi u ovom worktree-u (`task/DENT-006-raspored-svi-doktori`), potpuno paralelno sa Claude-ovim DENT-007 (lokalni backend za web zahtjeve) — nema preklapanja putanja, provjereno kroz `python scripts/coordination.py status` prije početka.
