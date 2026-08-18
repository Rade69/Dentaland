---
task_id: DENT-015
risk: MEDIUM
implementer: pi-ili-crush
reviewer: claude
status: ASSIGNED
created_at: 2026-08-18
---

# Task Contract — DENT-015: podaci za štampu rasporeda

Porijeklo: Codex-ov prijedlog za štampu (dashboard "Štampa" dugme, do
sada placeholder — `desktop/views/main_window.py::_on_print()`).
Podijeljeno na dva paralelna zadatka bez kolizije — ovo je SAMO sloj
podataka (bez Qt), GUI/rendering ide kroz DENT-016 (Codex), koji
konzumira ono što ovaj zadatak proizvede.

```yaml
id: DENT-015
title: Servisni sloj za štampu dnevnog/sedmičnog rasporeda — privatnost po dizajnu
risk: MEDIUM
objective: >
  Dodati funkcije koje sastavljaju "za-štampu spreman" prikaz rasporeda
  za jedan dan ili jednu sedmicu, sa STRUKTURNOM minimizacijom podataka
  (ne "zaboravi da prikažeš telefon", nego "tip podataka telefon uopšte
  nema polje za to") — isti obrazac kao `backend/notifications.py`
  (DENT-011), gdje `_compose_message` ne prima uslugu/doktora u
  potpisu, pa curenje nije ni moguće kroz taj kod.
allowed_paths: [src/dentaland/services/print_schedule.py, tests/test_print_schedule.py, agent_reports/DENT-015-task-contract.md, agent_reports/2026-08-18-DENT-015-print-schedule-data.md]
forbidden_paths: [desktop/, backend/, web/, src/dentaland/models.py, migrations/, src/dentaland/services/booking.py, src/dentaland/services/requests.py, CLAUDE.md, AGENTS.md]
objective_detalji: >
  Nov fajl `src/dentaland/services/print_schedule.py`. NE mijenjati
  `booking.py`/`requests.py` — samo ih POZIVATI (već postoje testirane
  funkcije: `AppointmentService.all_combined()`, `time_off_for_week()`,
  `breaks_for_week()`). Ako nešto nedostaje u tim fajlovima, to je
  `OUT_OF_SCOPE_FINDING`, ne razlog da se dirne fajl van allowed_paths.

  1. Nova dataclass `PrintScheduleEntry`:
     - `time_range: str` (npr. "09:00–09:30", već formatirano — GUI sloj
       ne treba da zna kako se datetime formatira za štampu)
     - `patient_name: str`
     - `doctor_name: str`
     - `service: str`
     - `status_label: str` (npr. "Potvrđen"/"Čeka potvrdu"/"Stigao"/
       "Završen" — ISTI srpski tekstovi kao u `desktop/views/week_view.py`
       `status_icon()`/statusnoj legendi iz DENT-009, radi dosljednosti;
       pogledati taj kod prije pisanja teksta, ne izmišljati novi)

     **NAMJERNO NEMA:** `phone`, `email`, `note`/napomena polja. Ne
     dodavati ih "za svaki slučaj" — tip podataka strukturno ne smije
     moći da nosi ta polja, to je cijela poenta ovog zadatka.

  2. Nova dataclass `PrintScheduleBlock` (za odsustva/pauze):
     - `time_range: str`
     - `doctor_name: str`
     - `label: str` (npr. "Van ordinacije", "Pauza")

  3. Nova dataclass `PrintSchedule` (rezultat za jedan poziv):
     - `title: str` (npr. "Ponedjeljak, 18.08.2026." ili "18.08. – 23.08.2026.")
     - `entries: list[PrintScheduleEntry]` (sortirano po vremenu)
     - `blocks: list[PrintScheduleBlock]` (sortirano po vremenu)

  4. `build_day_schedule(service: AppointmentService, day: date) -> PrintSchedule`
     — termini tog dana. **Isključiti** `CANCELLED`/`NO_SHOW` (operativni
     raspored, ne istorijski log — ovo je eksplicitan Codex-ov prijedlog,
     ima smisla: štampan papir je za DANAŠNJI rad, ne za arhivu). Uključiti
     blockout/pauza blokove za taj dan (poziva postojeće
     `time_off_for_week`/`breaks_for_week` pa filtrira na jedan dan, ili
     traži da se doda uzana dnevna varijanta ako je to čistije — po tvom
     nahođenju, oba su prihvatljiva).

  5. `build_week_schedule(service: AppointmentService, week_start: date) -> PrintSchedule`
     — isto za cijelu prikazanu sedmicu (Pon–Sub, 6 dana — vidi
     `WeekView.DAY_COUNT` u `desktop/views/week_view.py` za trenutnu
     odluku, ne pretpostavljaj 5 ni 7 dana). `title` treba da pokrije
     puni raspon (od-do datum).

  6. Usluga (`service`) SE prikazuje (potvrđena poslovna odluka,
     18.8.2026) — telefon/email/napomena NIKAD, ni na dan ni na
     sedmicu.
acceptance:
  - PrintScheduleEntry/Block/Schedule nemaju phone/email/note polja u tipu (provjerljivo — nema tih atributa na klasi).
  - build_day_schedule isključuje CANCELLED/NO_SHOW termine.
  - build_week_schedule pokriva tačno onoliko dana koliko WeekView.DAY_COUNT trenutno definiše (ne hardkodovano 5 ni 7).
  - Blockout/pauza blokovi se pojavljuju u oba (dan/sedmica) kad postoje u tom rasponu.
  - status_label tekstovi se poklapaju sa postojećom statusnom legendom iz DENT-009 (nema novoizmišljenih formulacija).
  - Entries i blocks su sortirani hronološki.
  - Nula Qt/PySide6 importa u ovom fajlu (čist servisni sloj, GUI sloj DENT-016 radi rendering).
verification: [pytest tests/test_print_schedule.py -v, pytest tests/ -q, ruff check src/dentaland tests, mypy src/dentaland]
review:
  reviewers: 1
  required: [security, scope]
```

## Napomena o procesu

Task Contract napisan i sačuvan u fajl PRIJE koda (naučena lekcija iz
DENT-002 incidenta ranije u projektu). Ovaj zadatak i DENT-016 (Codex,
GUI/rendering) dirinu POTPUNO različite fajlove — nema potrebe za
posebnom koordinacijom osim standardnog `coordination.py claim`.

`security` je obavezan review fokus jer je cijela svrha zadatka
minimizacija podataka na dokumentu koji fizički napušta računar
(papir/PDF) — greška ovdje je gora nego greška u internom prikazu, jer
se papir može izgubiti/vidjeti od nekog ko ne treba.
