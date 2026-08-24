---
task_id: REF-03
risk: MEDIUM
implementer: crush
reviewers: [codex, claude]
reviewer: codex
verdict: REJECT
commits: [e8d1ab7]
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
  - "F1 tests/test_ref03_booking_split.py:21-35 — string-based provjere facade-a propuštaju stvarni appointment CRUD/overlap SQL koji izbjegne nekoliko tačnih stringova; nakon dodavanja raw SELECT nad appointments sa start/end overlap uslovima oba ciljna testa i dalje prolaze (2 passed), pa testovi daju lažni PASS za ključnu granicu REF-03."
```

## Zaključak

Produkcijska podjela trenutno izgleda behavior-compatible, puni gate-ovi su
zeleni i scope je čist. Review je `REJECT` jer ključni novi arhitektonski
testovi ne padaju kada se u `booking.py` vrati upravo ona SQL/overlap logika
čije odsustvo tvrde da dokazuju.

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

URAĐENO: REJECT — gate-ovi i REF-00 contract prolaze, ali F1 pokazuje da oba
ključna string testa propuštaju stvarni CRUD/overlap SQL u facade-u.

NE DIRATI: produkcijsku implementaciju bez novog nalaza; F1 je ograničen na
kvalitet `tests/test_ref03_booking_split.py`.

SLJEDEĆE: Crush mijenja F1 testove tako da ne zavise od tačnog formatiranja,
Codex ponavlja raw-SQL i alternativni-SQLAlchemy mutacioni test. Claude review
ide tek poslije Codex PASS re-review-a, zatim Radovan human approval.
