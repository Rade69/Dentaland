---
task_id: DENT-003
risk: MEDIUM
implementer: crush
reviewers: [claude]
verdict: PASS_WITH_NOTES
commits: []
created_at: 2026-08-16
---

# DENT-003 — Servisni sloj (provjera preklapanja) + vezivanje GUI-ja

## Task Contract

Pun tekst u `agent_reports/DENT-003-task-contract.md`. Suština: servisni sloj
(CRUD + provjera preklapanja) kao drop-in zamjena za `FakeStore`, minimalan
izbor doktora u GUI, lista usluga iz prave `Service` tabele, i popravka da
drag&drop čuva trajanje termina.

## Šta je urađeno

- `src/dentaland/services/booking.py` — `AppointmentDTO`/`DoctorDTO` (plain
  dataclass, ne SQLAlchemy objekti), `OverlapError`, `AppointmentService`
  (create/get/all/move/services/doctors/set_doctor), provjera preklapanja po
  `doctor_id` + `status==SCHEDULED` + `start_time < end AND end_time > start`
  (ispravno za bilo koje trajanje), `ensure_seed_data()` (3 doktora + 5 usluga),
  `AppointmentService.from_sqlite(path)` factory.
- `src/dentaland/services/__init__.py` — re-export.
- `desktop/app.py` — `AppointmentService.from_sqlite("dentaland.db")` umjesto
  `FakeStore.seeded(...)`; bez SQLAlchemy/FakeStore importa.
- `desktop/views/main_window.py` — doctor dropdown (popunjen iz `store.doctors()`
  ako postoji; `FakeStore` ga nema pa se preskače), `set_doctor` + refresh na
  promjenu, `OverlapError` handling pri unosu.
- `desktop/views/week_view.py` — `move_appointment_to_slot` čuva trajanje
  (`new_end = new_start + (appt.end - appt.start)`), hvata `OverlapError`.
- `tests/test_services.py` — 10 testova.

## Verifikacija (stvarni rezultati)

| Komanda | Rezultat |
|---|---|
| `pytest tests/test_services.py -v` | 10 passed |
| `pytest tests/test_gui -v` | 9 passed |
| `pytest` (cijeli suite) | 33 passed |
| `ruff check src/dentaland desktop tests` | All checks passed |
| `grep -ri sqlalchemy desktop/views` | prazno (OK) |

## OUT_OF_SCOPE_FINDING

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  WeekView._appointments_by_cell() mapira termin na samo jednu ćeliju (početni
  slot). Termin duži od SLOT_MINUTES (30 min) ne "zauzima" vizuelno naredne
  ćelije koje realno pokriva, pa drag&drop na takvu ćeliju prolazi GUI-side
  provjeru, ali ga backend (servis) ispravno odbija OverlapError. Backend
  provjera je tačna (test_preklapanje_termina_duzeg_od_slota); GUI prikaz ne
  reflektuje pun raspon termina.
location: desktop/views/week_view.py::_appointments_by_cell / refresh
risk: MEDIUM
proposed_task: >
  Prikaz termina preko svih ćelija koje pokriva (spanning ili više itema) u
  WeekView.refresh(), da vizuelna zauzetost odgovara stvarnom rasponu.
```

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  Novi termini se i dalje prave sa fiksnih 30 min (DEFAULT_DURATION_MINUTES),
  jer AppointmentDialog (forbidden_path) ne nudi izbor trajanja usluge.
  Servis prima start/end eksplicitno, pa kad dijalog dobije trajanje, create
  će ga proslijediti bez dalje izmjene servisa.
location: desktop/views/main_window.py::_on_slot_selected
risk: LOW
proposed_task: >
  AppointmentDialog: prikaz trajanja odabrane usluge (Service.trajanje_min) i
  računanje end = start + trajanje_min pri unosu.
```

## Odbačene opcije

- Provjera preklapanja u WeekView (GUI) — odbačeno: backend (servis) je
  konačni autoritet; GUI `_appointments_by_cell` ima poznat bug.
- `phone/email/note` kao `str | None` u DTO — odbačeno: fake `Appointment`
  ima `str`; DTO normalizuje `None → ""`.
- Seed inline u `app.py` — odbačeno: `ensure_seed_data`/`from_sqlite` u servisu
  drži app.py tankim i seed testabilnim.

## Review (Claude, 16.8.2026)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisno pročitan cio `booking.py`, diff na sve tri `desktop/` datoteke, i `test_services.py`. Nezavisno ponovo pokrenuto (ne preuzeto iz izvještaja): `pytest tests/` u worktree-u → 33 passed, `ruff check src/dentaland desktop tests` → čist, `grep -ri sqlalchemy desktop/views/*.py` → prazno, `git diff --stat` na svih šest `forbidden_paths` (models.py, migrations/, fake_data.py, appointment_dialog.py, CLAUDE.md, AGENTS.md, docs/) → prazno, potvrđeno netaknuto.

Svih sedam acceptance stavki potvrđeno:

- Provjera preklapanja je ispravna intervalna logika (`start_time < end AND end_time > start`), sa `[)` granicom testiranom eksplicitno (`test_preklapanje_termina_duzeg_od_slota` — termin tačno na kraju prethodnog je dozvoljen, tačno isti obrazac kao budući `EXCLUDE` constraint iz v3.1 plana).
- `move()` ispravno isključuje sopstveni ID iz provjere preklapanja prije nego upiše novu poziciju — bez ovoga bi svaki move "preklapao sam sa sobom".
- CANCELLED/COMPLETED/NO_SHOW ne blokiraju slot — sve tri eksplicitno testirane, ne samo jedna kao reprezentativna.
- Doctor dropdown je urađen bez rušenja postojećih GUI testova (defanzivna `getattr` provjera) — pametno rješenje koje izbjegava nepotrebnu izmjenu test fixture-a.
- `week_view.py` popravka trajanja je tačno ono što je traženo.
- Nula SQLAlchemy importa u `desktop/views/` — arhitekturno pravilo i dalje poštovano.

**Oba prijavljena OUT_OF_SCOPE_FINDING su legitimna i ispravno odgođena, ne prećutana** — backend je konačni autoritet i ispravno odbija (dokazano testom) čak i tamo gdje GUI prikaz ne reflektuje pun raspon; disciplina da se ne dira `AppointmentDialog` (forbidden_path) je poštovana umjesto da se problem "riješi" zaobilaznim editovanjem zabranjene putanje.

**Nalaz koji implementer nije prijavio (LOW, ne blokira):** `mypy src/dentaland desktop` sada javlja 8 grešaka naspram 7 koje već postoje na `main` prije ovog zadatka (mypy nije bio dio DENT-002 verifikacije ni mog tadašnjeg review-a — moj propust, ne ovog zadatka). Neto +1 nova: `MainWindow.__init__` je izgubio eksplicitan tip za `store` (bio `FakeStore`, sad netipizovano jer prima i `AppointmentService`), i `_on_doctor_changed` pristupa `self.doctor_combo.currentData()` bez suženja da `doctor_combo` nije `None` (funkcionalno bezbjedno — callback se povezuje samo kad je combo izgrađen — ali mypy to ne može statički dokazati). Predlažem `Protocol` tip za `store` (npr. `BookingStore`) u budućem sitnom zadatku, i `assert self.doctor_combo is not None` u `_on_doctor_changed`. Mypy nije bio u `verification` listi ovog Task Contracta, pa ne blokira — ali vrijedi dodati mypy u standardnu verifikacionu listu ubuduće da ovakav drift ne prođe neopaženo.

**Dodatna sitnica, LOW:** `AppointmentService.get()` ne filtrira po `doctor_id` (za razliku od `all()`/`move()`) — trenutno nije iskoristivo kroz GUI jer se prikazuju samo termini odabranog doktora, ali je nekonzistentno sa ostatkom API-ja.

Verdikt: **PASS_WITH_NOTES**. Spremno za human approval.

## Integration status

MERGED → INTEGRATION_VERIFIED → DONE. Mergovano u `main` (commit `453272d`, merge commit poslije). Post-merge integration gate: pun test suite (43/43), `ruff check` na cijelom repou, grep provjera arhitekturnog pravila — svi prošli.
