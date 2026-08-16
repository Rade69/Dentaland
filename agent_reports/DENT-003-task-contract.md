---
task_id: DENT-003
risk: MEDIUM
implementer: crush
reviewer: claude
status: REVIEWED — vidi 2026-08-16-DENT-003-servisni-sloj.md za pun izvještaj
created_at: 2026-08-16
---

# Task Contract — DENT-003

```yaml
id: DENT-003
title: Faza 0 — Servisni sloj (provjera preklapanja) i vezivanje GUI-ja na prave modele
risk: MEDIUM
objective: >
  Implementirati servisni sloj koji desktop GUI koristi UMJESTO fake podataka
  (desktop/fake_data.py ostaje netaknut — i dalje koristan za izolovane GUI
  testove, ne briše se). Servisni sloj radi CRUD termina nad SQLAlchemy
  modelima iz DENT-001 (src/dentaland/models.py, već mergovano u main),
  sa provjerom preklapanja termina prije kreiranja/pomjeranja: isti
  doctor_id, aktivan status (SCHEDULED — Faza 0 nema PENDING), vremenski
  preklapajući raspon → odbiti sa jasnom greškom. CANCELLED/COMPLETED/
  NO_SHOW ne blokiraju slot (konzistentno sa budućim EXCLUDE constraint
  pravilom iz docs/dentaland-razvojni-plan-v3.1.md, iako Faza 0 SQLite
  nema DB-level constraint — provjera je na nivou servisnog sloja).

  Zamijeniti FakeStore sa pravim servisom u desktop/app.py, zadržavajući
  ISTI oblik interfejsa (create/get/all/move/services) da desktop/views/
  ne treba mijenjati logiku, samo izvor podataka. desktop/views/ i dalje
  NIKAD ne uvozi SQLAlchemy direktno — servisni sloj vraća plain DTO
  oblik (slično fake_data.Appointment: patient_name/phone/email/service/
  note/start/end), ne SQLAlchemy model objekte direktno u GUI.

  Dodati minimalan izbor doktora u GUI (dropdown ili tabovi u
  main_window.py) — pošto se sad gradi za sva tri doktora (Ljubo/Zorka/
  Ana, vidi CLAUDE.md "Šta je Dentaland"), prikaz mora filtrirati na
  jednog odabranog doktora odjednom. Ovo je minimalna nužna dopuna, NE
  redizajn — jedan dropdown, default prvi doktor.

  IZVAN OBIMA (namjerno, ne raditi): poštovanje working_hours/time_off
  pri prikazu (graying out slotova van radnog vremena) — WeekView i dalje
  koristi fiksan 08:00–18:00 grid. Ovo je budući zadatak, ne DENT-003.
allowed_paths: [src/dentaland/services/**, desktop/app.py, desktop/views/main_window.py, desktop/views/week_view.py, tests/test_services.py, agent_reports/**]
forbidden_paths: [src/dentaland/models.py, migrations/**, desktop/fake_data.py, desktop/views/appointment_dialog.py, CLAUDE.md, AGENTS.md, docs/**]
acceptance:
  - Kreiranje termina preko servisnog sloja provjerava preklapanje — dva aktivna termina istog doktora u preklapajućem rasponu ne mogu oba postojati, drugi zahtjev se odbija.
  - Pomjeranje termina (drag&drop) prolazi kroz istu proveru prije izvršenja.
  - CANCELLED/COMPLETED/NO_SHOW ne blokiraju slot.
  - desktop/app.py koristi servisni sloj umjesto FakeStore; desktop/views/ i dalje ima nula SQLAlchemy importa (provjerljivo grep-om).
  - GUI ima minimalan izbor doktora, prikaz filtrira na odabranog.
  - Lista usluga u dijalogu za unos dolazi iz prave Service tabele (naziv), ne hardkodovane liste.
  - Testovi pokrivaju — uspješno kreiranje bez konflikta, odbijanje preklapajućeg termina, uspješno i odbijeno pomjeranje, da otkazan/završen termin ne blokira slot.
  - **Pomjeranje termina (drag&drop) čuva ORIGINALNO trajanje** — `WeekView.move_appointment_to_slot()` trenutno hardkoduje novi kraj kao `start + SLOT_MINUTES` (uvijek 30 min, vidi nalaz u `agent_reports/2026-08-16-DENT-002-gui-shell.md`), što bi tiho skraćivalo termine dužim od 30 min čim stignu prave usluge sa varijabilnim `trajanje_min`. Popraviti da novi kraj bude `new_start + (appt.end - appt.start)`.
  - **Provjera preklapanja mora raditi ispravno i za termine duže od jednog slota** — trenutni `_appointments_by_cell()` mapira termin na samo JEDNU ćeliju (početni slot), pa termin od npr. 60 min ne "zauzima" narednu ćeliju koju realno pokriva. Servisni sloj (backend provjera) mora ispravno detektovati preklapanje bez obzira na ovo — ako se GUI-strana `_appointments_by_cell` logika ne popravlja u ovom zadatku (prihvatljivo ako je previše obimno), prijaviti kao `OUT_OF_SCOPE_FINDING` sa jasnim opisom, ne prećutati.
verification:
  - pytest tests/test_services.py -v
  - pytest tests/test_gui -v  # postojeći GUI testovi i dalje moraju proći (rade nad FakeStore fixture-om, ne mijenjaju se)
  - ruff check src/dentaland desktop tests
  - "grep -ri sqlalchemy desktop/views  # očekivano prazno (osim docstring napomena)"
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena o dizajnu

`desktop/fake_data.FakeStore` je namjerno ostao netaknut kao referentni oblik interfejsa (create/get/all/move/services) — servisni sloj treba da bude "drop-in" zamjena istog oblika, samo backed pravim modelima umjesto in-memory dict-a. To znači field-name prevod: fake `patient_name/phone/note/service/start/end` ↔ pravi model `ime/telefon/napomena/service_id→naziv/start_time/end_time`. Ova konverzija ide unutar servisnog sloja, GUI kod se ne dira osim za doktor-selector.
