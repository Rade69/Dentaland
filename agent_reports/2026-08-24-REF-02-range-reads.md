---
task_id: REF-02
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-24
---

# REF-02 — Range-based scheduling reads + eager loading

## Task Contract

Izvor: `agent_reports/REF-02-task-contract.md` (napisan PRIJE koda). Zavisnost
REF-01 potvrđena (main HEAD `4e45212`, granano sa njega). MEDIUM risk, dva
reviewera (Codex pa Claude).

## Šta je urađeno

1. **`AppointmentService.appointments_for_range(range_start, range_end,
   doctor_id=None)`** (novo u `booking.py`):
   - intervalska overlap semantika `start_time < range_end AND end_time >
     range_start` (isti obrazac kao `validate_appointment_overlap` iz REF-01);
   - isključuje PENDING/REJECTED (kao `all_combined`), sort po `start_time`;
   - `selectinload(Appointment.doctor)` + `selectinload(Appointment.service)`
     (bez N+1);
   - opcioni `doctor_id` filter.
2. **`day_view.py`** — `_fetch_appointments` sada poziva
   `appointments_for_range(day_start, day_end)` umjesto `all_combined()`, i
   zadržava postojeći `start.date() == day` filter (isti prikaz).
3. **`week_view.py`** — `_fetch_appointments` poziva
   `appointments_for_range(week_start, week_start+6d)`, fallback na
   `store.all()` kao prije (FakeStore kompatibilnost).
4. **`all_combined()` ostaje NETAKNUTA** (koristi je `print_schedule.py`).

## Changed files (sve u allowed_paths)

- `src/dentaland/services/booking.py` — nova metoda + `selectinload` import.
- `desktop/views/day_view.py` — range read.
- `desktop/views/week_view.py` — range read.
- `tests/test_ref02_range_reads.py` — 6 novih testova.
- `agent_reports/REF-02-task-contract.md` + ovaj izvještaj.

`print_schedule.py`, `availability.py`, `requests.py`, `main_window.py`,
`models.py`, `migrations/` — NIJEDAN nije diran.

## Performance evidence — PRIJE / POSLIJE (5000 istorijskih termina, 3 doktora, 100 servisa)

```text
PRIJE  all_combined (ceo skup)      : 5000 redova, 104 SQL upita
POSLIJE appointments_for_range(1d)  :   32 redova,   3 SQL upita
POSLIJE appointments_for_range(6d)  :  272 redova,   3 SQL upita
```

| Metrika | PRIJE (`all_combined`, netaknut) | POSLIJE (`appointments_for_range`) |
|---|---|---|
| Dan | 5000 redova, 104 upita | 32 reda, 3 upita |
| Sedmica (6 dana) | 5000 redova, 104 upita | 272 reda, 3 upita |

### Nalaz o N+1 (korekcija pretpostavke iz instrukcije, mjereno)

Instrukcija je pretpostavila "svaki termin u petlji radi zaseban lazy-load
SELECT za doctor i service" → očekivani N+1 = ~2·N upita. Mjerenje to **ne
potvrđuje doslovno**: SQLAlchemy identity map kešira relationship po
RAZLIČITOM entitetu, pa je broj lazy upita `1 + (broj različitih doktora) +
(broj različitih servisa)`, ne `1 + 2·N`.

- Sa 3 doktora + 1 servis (realan seed): lazy = **5 upita**, ne 10001.
- Sa 3 doktora + 100 servisa (naglašen scenario): lazy = **104 upita** — N+1
  se manifestuje kroz broj različitih servisa, ne kroz broj termina.

`selectinload` to fiksira na **konstantna 3 upita** bez obzira na broj
doktora/servisa/termina. Glavni dobitak taska je **range filter** (5000 → 32
reda), a eager load je sekundaran ali ispravan (konstantan broj upita).

## Verifikacija (rezultati)

```text
pytest tests/ -q
→ 328 passed, 11 warnings   (322 baseline + 6 novih test_ref02_range_reads)

ruff check src/dentaland desktop backend tests
→ All checks passed!, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 38 source files
```

GUI behavior očuvan: svi postojeći GUI testovi (test_gui/) prolaze
nepromijenjeni — Day/Week prikazuju iste termine, samo dohvaćene kroz range.

## Acceptance

- [x] DayView koristi `appointments_for_range` (ne cijelu istoriju);
- [x] WeekView koristi `appointments_for_range`;
- [x] overlap semantika testirana na terminu preko ponoći (vraća se u oba
      dana) i preko kraja sedmice (sub 23:00 → ned 01:00);
- [x] eager-loading dokazano PRIJE/POSLIJE brojkama (104→3 upita);
- [x] nema GUI behavior promjene (postojeći testovi zeleni);
- [x] `print_schedule.py` i dalje koristi netaknut `all_combined()`
      (postojeći print testovi zeleni).

## Review

`PENDING` — Codex (test kvalitet, prvi), pa Claude (arhitektura). Radovan
human approval obavezan prije merge-a.

## Integration status

`NOT_MERGED` — čeka dva review-a.

## Handoff

CILJ: Day/Week ne čitaju cijelu istoriju + eager load bez N+1.

URAĐENO: `appointments_for_range` sa overlap semantikom i `selectinload`,
Day/Week prebačeni, 6 testova, PRIJE/POSLIJE mjerenje.

NE DIRATI: `all_combined` (za print), `print_schedule.py`, `availability.py`,
`requests.py`, `main_window.py`, `models.py`, `migrations/`.

SLJEDEĆE: Codex review → Claude review → Radovan human approval → merge.
