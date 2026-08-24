---
task_id: REF-03
risk: MEDIUM
implementer: codex
reviewers: [fresh-reviewer-1, claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-24
---

# REF-03 — F1 body-shape fix nakon Codex review runde 3

## Procesna odluka

Radovan je eksplicitno naredio da Codex preuzme implementaciju nakon tri
neuspjele Crush popravke. Time prethodni Codex Reviewer 1 više nije nezavisan
review za finalni fix. Potreban je novi Reviewer 1 iz druge sesije/agenta,
zatim Claude Reviewer 2 i Radovan human approval.

## Root cause

Allowlist iz commita `5a1acd0` pregledao je samo `ast.Call` čvorove i broj
delegacijskih poziva. Dodatna naredba bez poziva, npr.
`self.doctor_id = 999`, mogla je stajati prije legitimne delegacije, a cijeli
`tests/test_ref03_booking_split.py` je i dalje prolazio (`6 passed`).

## Fix

Promijenjen je samo `tests/test_ref03_booking_split.py`:

- javna metoda smije imati samo jedan delegacijski statement; ili
- lokalni `name = self._require_doctor()` bez argumenata, zatim jedan
  delegacijski statement;
- assignment na `self`, dodatne naredbe i neočekivane privatne metode padaju;
- dozvoljeni modul mora izlagati stvarnu callable funkciju sa tačno jednim
  dotted segmentom (`appointments.fn`, `availability.fn`, `settings.fn`);
- argumenti delegacije smiju biti samo proslijeđena lokalna imena ili
  `self._session_factory`, bez poziva/walrus/dinamičkog izraza.

Produkcijski `src/dentaland/services/booking.py` nije mijenjan.

## Repro poslije fixa

Sve mutacije su rađene u izolovanoj kopiji i uklonjene nakon testa.

### State side effect

```python
def mark_arrived(self, appt_id):
    self.doctor_id = 999
    return appointments.mark_arrived(self._session_factory, appt_id)
```

Test sada pada sa:

```text
AppointmentService.mark_arrived mijenja state prije delegacije:
self.doctor_id = 999
```

### Raw SQL

Privatna metoda sa `session.execute(text("SELECT * FROM appointments ..."))`
ruši oba strukturna testa: nedozvoljeni pozivi i neočekivana privatna metoda.

### Aliasirani SQLAlchemy

Privatna metoda sa `from sqlalchemy import select as sel` i
`sel(Doctor).where(...)` ruši oba strukturna testa.

### Dinamički execute

Privatna metoda sa `getattr(session, "execute")` i pozivom kroz lokalnu
varijablu ruši oba strukturna testa.

## Standardna verifikacija

```text
pytest tests/ -q
336 passed, 11 warnings in 19.82s (exit 0)

ruff check src/dentaland desktop backend tests
All checks passed! (exit 0)

mypy src/dentaland desktop backend
Success: no issues found in 40 source files (exit 0)
```

## Handoff

CILJ: zatvoriti F1 lažni PASS za dodatne naredbe u tankom facade-u.

URAĐENO: kompletno tijelo javne facade metode sada ima strogo dozvoljen AST
oblik; četiri adversarne mutacije daju stvarni FAIL, puni gate je zelen.

NE DIRATI: `src/dentaland/services/booking.py` i ostali produkcijski moduli;
fix mijenja samo arhitektonski test.

SLJEDEĆE: novi nezavisni Reviewer 1 provjerava ovaj commit od nule, zatim
Claude Reviewer 2, pa Radovan human approval. Prethodni Codex review se ne
računa kao finalni nezavisni review jer je Codex sada implementer fixa.
