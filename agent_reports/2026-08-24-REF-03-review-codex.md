---
task_id: REF-03
risk: MEDIUM
implementer: crush
reviewers: [codex, claude]
reviewer: codex
verdict: REJECT
commits: [e8d1ab7, 6e5680c]
created_at: 2026-08-24
---

# REF-03 — Codex review (test kvalitet)

```yaml
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
blocking_findings:
  - "F1 tests/test_ref03_booking_split.py:37-96 — AST denylist hvata direktni text/execute oblik, ali propušta aliasirani `select as sel` i dinamički `getattr(session, 'execute')`; alternativni SQLAlchemy oblik daje svih 6 passed, a dinamički execute oba ključna testa zelena (2 passed)."
```

## Finalni zaključak — re-review runda 2

Commit `6e5680c` popravlja prvobitni raw-SQL slučaj, ali F1 nije zatvoren:
novi AST denylist i dalje daje lažni PASS za dva druga data-access oblika.
Finalni Codex verdikt ostaje `REJECT`.

### Runda 2 — standardni gate

```text
pytest tests/ -q
336 passed, 11 warnings in 18.60s (exit 0)

ruff check src/dentaland desktop backend tests
All checks passed! (exit 0)

mypy src/dentaland desktop backend
Success: no issues found in 40 source files (exit 0)
```

Fix diff `cde97ce..6e5680c` mijenja samo
`tests/test_ref03_booking_split.py` i dodaje `agent_reports/**` evidence.
`booking.py` nije dirnut.

### Mutacija 1 — direktni raw SQL: zatvoreno

Ponovljena privatna metoda sa
`session.execute(text("SELECT * FROM appointments ..."))` sada ruši
`test_booking_facade_ne_sadrzi_sql_data_access`. Stvarni nalaz testa je
`AppointmentService._hidden_raw_sql sadrži data-access poziv`.

### Mutacija 2 — aliasirani SQLAlchemy select: još prolazi

U facade je privremeno dodano:

```python
from sqlalchemy import select as sel

def _hidden_aliased_select(self):
    return sel(
        Doctor
    ).where(
        Doctor.id > 0
    )
```

Stvarni rezultat cijelog REF-03 arhitektonskog fajla:

```text
6 passed in 0.40s
```

AST provjera poredi samo `ast.Name.id` sa literalnim imenom `select`, bez
razrješavanja import aliasa.

### Mutacija 3 — dinamički execute: još prolazi

U facade je dodatno privremeno dodano:

```python
run_query = getattr(session, "execute")
return list(run_query("SELECT * FROM appointments"))
```

Stvarni rezultat data-access i delegation testa:

```text
2 passed in 0.36s
```

Pozitivna provjera delegacije preskače privatne metode, a denylist ne prati
`getattr`/lokalni alias poziva. Fix treba dokazati granicu bez oslanjanja na
otvorenu listu sintaksnih oblika koju je lako zaobići; oba navedena oblika
moraju biti uključena u sljedeću adversarnu provjeru.

## Precondition i scope

Worktree je zatečen sa osam nekomitovanih task fajlova. Bez izmjene sadržaja
zamrznut je implementer commit `e8d1ab7`, pušovan na
`origin/task/REF-03-booking-split`, a remote SHA je zatim potvrđen kao
`e8d1ab7225cd8669f317fe293611cbcab6092788`.

`git diff --stat f1b7acb..e8d1ab7` sadrži samo dozvoljene putanje:

- `.agent/PROJECT_MAP.md`;
- `src/dentaland/services/{booking,appointments,availability,settings}.py`;
- `tests/test_ref03_booking_split.py`;
- dva REF-03 fajla u `agent_reports/**`.

Nisu dirnuti `desktop/**`, `requests.py`, `print_schedule.py`, `backend/**`,
`models.py` ni `migrations/**`.

## Verifikacija

```text
pytest tests/ -q
336 passed, 11 warnings in 11.48s (exit 0)

pytest tests/test_ref00_service_api_contract.py -q
9 passed in 0.41s (exit 0)

ruff check src/dentaland desktop backend tests
All checks passed! (exit 0)

mypy src/dentaland desktop backend
Success: no issues found in 40 source files (exit 0)
```

REF-00 API contract fajl je nepromijenjen i prolazi, pa facade zadržava
javni surface koji taj safety net pokriva.

## F1 — adversarni lažni PASS

U izolovanoj kopiji commita u `AppointmentService` je dodana privatna metoda
koja izvršava:

```sql
SELECT * FROM appointments
WHERE start_time < :range_end AND end_time > :range_start
```

To je stvarni appointment SQL i overlap query u facade-u, suprotno glavnoj
REF-03 granici. Namjerno izbjegava tačne stringove koje testovi traže:
`select(Appointment)`, `session.get(Appointment`,
`Appointment.start_time < end` i `Appointment.end_time > start`.

Stvarni rezultat:

```text
pytest tests/test_ref03_booking_split.py -q
6 passed in 0.54s

pytest \
  tests/test_ref03_booking_split.py::test_booking_facade_ne_sadrzi_appointment_crud_sql \
  tests/test_ref03_booking_split.py::test_booking_facade_ne_implementira_overlap -q
2 passed in 0.46s
```

Fix treba provjeravati strukturu/ponašanje koje je zabranjeno, a ne nekoliko
format-sensitive stringova. Prihvatljiv pravac je AST provjera poziva/importa
i/ili stroža pozitivna provjera da javne facade metode imaju samo dozvoljeni
delegacijski oblik. Novi test mora biti adversarno pokazan na najmanje raw
SQL i razlomljenom/alternativnom SQLAlchemy izrazu.

## Import graf i nejasni slučajevi

Nezavisni import smoke test za `availability`, `appointments`, `settings` i
`booking` prolazi (`imports-ok`). Direktni servisni importi potvrđuju graf:
`appointments → availability`, `settings → appointments`, facade → sva tri;
nema povratnog importa koji bi napravio ciklus.

Grep za `list_working_hours` u `desktop/**` nalazi samo
`desktop/views/settings_panel.py:303`, što potvrđuje jedan od tri
implementerova obrazloženja. Testovi imaju još dva servisna poziva, ali nema
drugog desktop potrošača.

Ručni spot-check facade-a: `mark_arrived`, `mark_completed`, `move`,
`service_options`, `list_working_hours` i `set_working_hours` su čiste
delegacije. `create`/`all` dodatno pozivaju `_require_doctor`, što je
eksplicitno dozvoljena facade state provjera iz Task Contracta.

## Handoff

CILJ: dokazati da REF-03 testovi stvarno štite tanku facade granicu i javnu
kompatibilnost.

URAĐENO: REJECT — direktni raw SQL je sada uhvaćen, ali aliasirani SQLAlchemy
select i dinamički execute i dalje daju lažni PASS.

NE DIRATI: produkcijsku implementaciju bez novog nalaza; F1 je ograničen na
kvalitet `tests/test_ref03_booking_split.py`.

SLJEDEĆE: Crush zatvara alias/getattr rupe ili zamjenjuje otvoreni denylist
robustnijom granicom; Codex ponavlja sva tri mutaciona testa. Claude review
ide tek poslije Codex PASS re-review-a, zatim Radovan human approval.
