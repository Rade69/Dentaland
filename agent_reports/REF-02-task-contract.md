---
task_id: REF-02
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit d4b09e7, 2026-08-24), post-merge integration gate PASS (330 pytest, ruff, mypy)."
review_summary: >-
  Codex Reviewer 1 runda 1: REJECT (F1: eager-load test koristio samo 1
  doktora/1 servisa, lazy varijanta prolazila isti prag kao eager - lazan
  PASS; F2: nema testa za tacan dodir half-open granice, mutacija < u <=
  prolazila neopazeno). Pi popravio (4 doktora/6 servisa za F1, dva
  adjacency testa za F2). Codex runda 2: PASS. Claude Reviewer 2: PASS
  (arhitektura potvrdjena prije Codexovog review-a, ukljucujuci nezavisno
  PRIJE/POSLIJE mjerenje - 104/3 SQL upita - identicno Pi-jevoj i
  Codexovoj brojci).
created_at: 2026-08-24
merged_at: 2026-08-24
---

# REF-02 — Range-based scheduling reads + eager loading

## Task Contract

**Cilj:** Uvesti servisni read contract `appointments_for_range(range_start,
range_end, doctor_id=None)` sa intervalskom overlap semantikom, prebaciti
Day/Week view da ne čitaju cijelu istoriju, i uvesti eager loading
(`selectinload`/`joinedload`) da se ukloni N+1.

**Risk:** MEDIUM (dira servisni sloj + dva GUI view-a; dvostruki review za
REF paket).

Izvor: `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`, sekcija 9.

Zavisnost: REF-01 — potvrđeno mergovan (main HEAD `4e45212`).

## SQL semantika (ne izmišljati novi obrazac)

```text
Appointment.start_time < range_end
AND Appointment.end_time > range_start
```

Isti oblik intervalskog preklapanja kao `validate_appointment_overlap` iz
REF-01.

## Kontekst (potvrđen čitanjem koda)

- `booking.py` `all_combined()` (linije ~263-279): bira SVE termine svih
  doktora bez range filtera (isključuje PENDING/REJECTED), sort po
  `start_time`. **Ostaje netaknuta** (backward-compat).
- N+1: `_to_dto`/`_service_name` pristupaju `appt.service.naziv` i
  `appt.doctor.ime` kao lazy relationship — `all_combined()` nema eager
  load, pa svaki red radi zaseban SELECT za doctor i service. Grep: NEMA
  nijedne postojeće upotrebe `selectinload`/`joinedload` u `src/dentaland/`
  — ovo uspostavlja prvi obrazac.
- Pozivaoci `all_combined()`: `day_view.py:113`, `week_view.py:247`
  (prebacujem na `appointments_for_range`), i `print_schedule.py:120`
  (**ne diram** — van scope-a, REF-07 će ga dotaknuti).

## Šta uraditi

1. Dodati `appointments_for_range(range_start, range_end, doctor_id=None)`
   u `AppointmentService`:
   - WHERE po overlap semantici + isključenje PENDING/REJECTED + opcioni
     `doctor_id` filter;
   - sort po `start_time`;
   - `selectinload`/`joinedload` za doctor i service (bez N+1).
2. Prebaciti `day_view.py` i `week_view.py` da koriste
   `appointments_for_range` umjesto `all_combined()` (isti GUI prikaz, drugi
   način dohvatanja).
3. `all_combined()` ostaje netaknuta (za `print_schedule.py`).
4. Performance evidence PRIJE/POSLIJE (vidi ispod).

## Performance evidence (obavezno PRIJE i POSLIJE)

- Test baza sa nekoliko hiljada istorijskih termina kroz više mjeseci.
- PRIJE: broj redova `all_combined()` vraća za Day/Week upit + broj SQL
  upita (SQLAlchemy `before_cursor_execute` brojač) — N+1 dokaz na starom
  kodu.
- POSLIJE: `appointments_for_range()` za isti period — broj redova
  (drastično manji) + broj SQL upita (konstantan, ne raste sa brojem
  termina).
- Obje brojke u izvještaju, jedna pored druge.

## Acceptance

- [ ] DayView ne koristi cijelu istoriju (koristi `appointments_for_range`);
- [ ] WeekView ne koristi cijelu istoriju;
- [ ] range overlap semantika testirana na terminima koji PRELAZE granicu
      dana/sedmice (termin koji počinje uveče a završava poslije ponoći,
      termin koji premošćuje kraj sedmice);
- [ ] eager-loading dokazano PRIJE/POSLIJE brojkama;
- [ ] nema GUI behavior promjene (isti termini, drugačije dohvaćeni);
- [ ] `print_schedule.py` i dalje radi identično (nedirano, postojeći testovi).

## Allowed paths

```text
src/dentaland/services/booking.py
desktop/views/day_view.py
desktop/views/week_view.py
tests/test_services.py
tests/test_ref02_range_reads.py    (novo)
agent_reports/**
```

## Forbidden paths

```text
src/dentaland/services/print_schedule.py
src/dentaland/services/availability.py
src/dentaland/services/requests.py
desktop/views/main_window.py
models.py
migrations/**
```

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline: 322 pytest passed (provjeriti tačan broj na svom worktree-u prije
početka, ne pretpostaviti).

## Review

Codex (test kvalitet, prvi) pa Claude (arhitektura). Radovan human approval
obavezan prije merge-a.

## Koordinacija

Worktree `Dentaland-worktrees/REF-02-range-reads`, grana
`task/REF-02-range-reads` (sa main-a `4e45212`). Claim prije početka.
