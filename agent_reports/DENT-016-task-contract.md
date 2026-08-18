---
task_id: DENT-016
title: Štampa dnevnog/sedmičnog rasporeda — GUI i rendering
risk: MEDIUM
implementer: crush
reviewer: claude
status: ASSIGNED
created_at: 2026-08-18
revised_at: 2026-08-18
---

# Task Contract — DENT-016: Štampa rasporeda (GUI/rendering)

Sadržaj zadatka je Codex-ov sopstveni prijedlog, ali implementaciju
radi **Crush** (18.8.2026 odluka — Codex ostaje fokusiran na popravke
čitljivosti kalendara koje je Radovan uočio nakon stvarnog korišćenja;
DENT-016 nije bio ni započet u tom trenutku, pa nema izgubljenog rada
prebacivanjem). Podijeljeno na dva paralelna dijela da bi moglo odmah
krenuti bez čekanja: **ovaj zadatak (DENT-016) je isključivo
GUI/rendering sloj**, podaci dolaze iz **DENT-015** (Pi,
`src/dentaland/services/print_schedule.py` — `PrintSchedule`/
`PrintScheduleEntry`/`PrintScheduleBlock` dataclass-e i
`build_day_schedule()`/`build_week_schedule()` funkcije). DENT-015
možda još nije gotov kad ovaj zadatak počne — GUI sloj se piše protiv
DOGOVORENOG interfejsa (vidi ispod), integracija/pravi test dolazi kad
oba budu spremna.

```yaml
id: DENT-016
title: Štampa rasporeda — meni, pregled, rendering dokumenta
risk: MEDIUM
objective: >
  "+ Štampa" dugme (trenutno placeholder, `_on_print()` u
  `desktop/views/main_window.py:507`) dobija stvarnu funkcionalnost:
  meni sa tri opcije, uvijek pregled prije štampe, rendering u
  QPrinter preko podataka iz DENT-015 (ne screenshot ekrana —
  potvrđeno ispravna odluka iz tvog prijedloga, izbjegava DPI/skaliranje
  probleme koje smo upravo vidjeli sa footer/DPI popravkom).
allowed_paths: [desktop/views/main_window.py, desktop/print_document.py, tests/test_gui/test_print_document.py, agent_reports/DENT-016-task-contract.md, agent_reports/2026-08-18-DENT-016-print-gui.md]
forbidden_paths: [src/dentaland/services/print_schedule.py, src/dentaland/services/booking.py, src/dentaland/services/requests.py, src/dentaland/models.py, migrations/, backend/, web/, CLAUDE.md, AGENTS.md]
objective_detalji: >
  Dogovoreni interfejs iz DENT-015 (piši protiv ovoga, ne čekaj da
  fajl fizički postoji da bi počeo raditi na GUI strani):

  ```python
  from dentaland.services.print_schedule import (
      PrintSchedule, PrintScheduleEntry, PrintScheduleBlock,
      build_day_schedule, build_week_schedule,
  )
  # PrintSchedule: title: str, entries: list[PrintScheduleEntry], blocks: list[PrintScheduleBlock]
  # PrintScheduleEntry: time_range, patient_name, doctor_name, service, status_label (sve str)
  # PrintScheduleBlock: time_range, doctor_name, label (sve str)
  # build_day_schedule(service: AppointmentService, day: date) -> PrintSchedule
  # build_week_schedule(service: AppointmentService, week_start: date) -> PrintSchedule
  ```

  1. Klik na "Štampa" otvara meni sa tri stavke (Codex-ov prijedlog,
     prihvaćen): "Štampaj prikazanu sedmicu", "Štampaj jedan dan…"
     (otvara mali date-picker ili koristi trenutno selektovani dan ako
     već postoji koncept "selektovanog dana" u kalendaru — po tvom
     nahođenju), "Sačuvaj kao PDF".
  2. Prije bilo kakve štampe UVIJEK `QPrintPreviewDialog`.
  3. Sedmica: A4 horizontalno (landscape), kolone Pon–Sub (onoliko
     kolona koliko `WeekView.DAY_COUNT` trenutno definiše). Dan: A4
     uspravno (portrait), hronološki spisak termina.
  4. Dokument sadrži: Dentaland logo (već postoji asset,
     `web/assets/logo.png` — provjeri da li desktop GUI već negdje
     učitava taj isti fajl, npr. iz DENT-009 brand bloka, radi
     konzistentnosti puta), naslov/datum-raspon iz `PrintSchedule.title`,
     i za svaki `entry`: `time_range`, `patient_name`, `doctor_name`,
     `service`, `status_label`. `blocks` (pauze/odsustva) prikazani kao
     vizuelno odvojeni sivi red/blok.
  5. **NIKAD ne renderovati telefon/email/napomenu** — ovo je
     osigurano već na nivou tipa u DENT-015 (ta polja ne postoje na
     `PrintScheduleEntry`), pa ovaj sloj strukturno ne može da ih
     procuri čak i greškom — ali svejedno ne pisati kod koji bi
     pokušao da im pristupi (npr. preko `AppointmentDTO` direktno,
     zaobilazeći `PrintSchedule`) — SVA štampa ide isključivo kroz
     `PrintSchedule`/`Entry`/`Block`, nikad direktno kroz `AppointmentDTO`.
  6. Tehnički: `QPrinter`, `QPrintPreviewDialog`, i generator dokumenta
     (npr. `QTextDocument` sa HTML/CSS tabelom, ili `QPainter` direktno
     — procijeni šta je jednostavnije za dvije različite orijentacije/
     layoute, ovo NIJE propisano, tvoja tehnička odluka).
acceptance:
  - "Štampa" dugme otvara meni sa tri opcije umjesto TODO poruke.
  - Print preview se uvijek prikaže prije stvarne štampe/PDF-a.
  - Sedmični layout je landscape, dnevni portrait.
  - Dokument sadrži logo, naslov, i sve entry/block podatke iz PrintSchedule.
  - Nigdje u renderovanom dokumentu nema telefon/email/napomena teksta (provjerljivo pretragom generisanog HTML-a/teksta u testu).
  - Sav pristup podacima ide kroz print_schedule.py tipove, ne direktno kroz AppointmentDTO.
  - Nula regresije u postojećim GUI testovima.
verification: [pytest tests/ -q, ruff check desktop tests, mypy desktop, "grep za phone/email/napomena u generisanom test dokumentu — očekivano prazno"]
review:
  reviewers: 1
  required: [architecture, security, scope]
```

## Napomena o procesu

Ovaj zadatak i DENT-015 (Pi) dirinu potpuno različite fajlove — nema
kolizije. Ako se pokaže da je dogovoreni interfejs iz DENT-015
nedovoljan (npr. treba još jedno polje), to je razlog za kratak dogovor
prije nastavka, ne za tiho proširivanje `print_schedule.py` iz ovog
zadatka (taj fajl je u `forbidden_paths` ovdje).

Usluga (`service`) SE prikazuje na štampi — potvrđena poslovna odluka
(18.8.2026), Codex-ova preporuka je prihvaćena.
