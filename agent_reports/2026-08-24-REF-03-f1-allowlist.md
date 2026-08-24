---
task_id: REF-03
risk: MEDIUM
implementer: crush
reviewers: [codex, claude]
status: "F1 runda 3 — allowlist umjesto denylist, adversarno potvrđeno na 4 oblika. Čeka Codex re-review."
related_review: agent_reports/2026-08-24-REF-03-review-codex.md
commit: 6e5680c (zamijenjen ovom rundom)
created_at: 2026-08-24
---

# REF-03 — F1, treći pokušaj: allowlist umjesto denylist

## Zašto je denylist odbačen

Codex je u dvije runde našao tri oblika izbjegavanja (raw SQL, aliasirani
`select as sel`, dinamički `getattr(session, "execute")`). Svaki denylist
dodatak otvara prostor za četvrti oblik — to je strukturna mana pristupa
"nabroji sve zabranjeno", ne slučajna nepažnja.

## Novi pristup: allowlist (pozitivna provjera)

Test `test_booking_facade_pozivi_su_samo_iz_allowlista` provjerava da tijelo
svake facade metode (osim `__init__`/`from_sqlite`/`set_doctor`/
`_require_doctor`) sadrži SAMO pozive čiji je root u dozvoljenom skupu:

```text
{appointments, availability, settings}            # moduli za delegaciju
{list_pending, confirm_request, reject_request}   # requests funkcije
{self._require_doctor}                            # facade-interni, bez SQL
```

`_dotted_name()` vraća pun kvalifikovani naziv poziva; za dinamičke pozive
(`getattr(...)()`, `session.__getattribute__(...)()`) vraća `None` jer je
`func` sam `ast.Call` — pa automatski padaju. Default je "odbij", ne
"dozvoli osim nabrojanih". Drugi test (`test_booking_facade_javne_metode_su_jedna_delegacija`)
dodatno zahtijeva tačno jedan delegacijski poziv po javnoj metodi kao
posljednji izraz.

## Adversarna provjera — stvaran output (4 oblika, ne parafraza)

### 1. Raw SQL (`text(...)`)

Mutacija dodaje privatnu metodu sa `session.execute(text("SELECT * FROM appointments ..."))`.

```text
$ python -m pytest tests/test_ref03_booking_split.py -q
E           AssertionError: AppointmentService._mut_raw_sql ima nedozvoljene pozive: ['self._session_factory()', "session.execute(text('SELECT * FROM appointments WHERE start_time < :re AND end_time > :rs'), {'re': range_end, 'rs': range_start})", "text('SELECT * FROM appointments WHERE start_time < :re AND end_time > :rs')"]
1 failed, 5 passed in 0.38s
```

### 2. Aliasirani import (`select as sel`)

Mutacija mijenja import u `from sqlalchemy import select as sel` i poziva `sel(Appointment)`.

```text
$ python -m pytest tests/test_ref03_booking_split.py -q
E           AssertionError: AppointmentService._mut_alias ima nedozvoljene pozive: ['sel(Appointment).where(Appointment.start_time < range_end, Appointment.end_time > range_start)', 'self._session_factory()', 'session.scalar(stmt)', 'sel(Appointment)']
1 failed, 5 passed in 0.38s
```

### 3. Dinamički `getattr(session, "execute")`

```text
$ python -m pytest tests/test_ref03_booking_split.py -q
E           AssertionError: AppointmentService._mut_getattr ima nedozvoljene pozive: ['self._session_factory()', "getattr(session, 'execute')('SELECT * FROM appointments WHERE start_time < :re AND end_time > :rs', {'re': range_end, 'rs': range_start})", "getattr(session, 'execute')"]
1 failed, 5 passed in 0.38s
```

### 4. Četvrti oblik (nov, nije ga Codex probao): `session.__getattribute__("execute")`

```text
$ python -m pytest tests/test_ref03_booking_split.py -q
E           AssertionError: AppointmentService._mut_getattribute ima nedozvoljene pozive: ['self._session_factory()', "session.__getattribute__('execute')('SELECT * FROM appointments WHERE start_time < :re AND end_time > :rs', {'re': range_end, 'rs': range_start})", "session.__getattribute__('execute')"]
1 failed, 5 passed in 0.38s
```

Napomena: u svakom output-u je i `self._session_factory()` — otvaranje
session-a — i samo po sebi nedozvoljen poziv (nije u allowlistu). To je
dodatna, fundamentalnija granica: facade ne smije ni otvarati session, a
kamoli izvršavati SQL.

### Čisto stanje

```text
$ git restore src/dentaland/services/booking.py
$ python -m pytest tests/test_ref03_booking_split.py -q
6 passed in 0.35s
```

## Verifikacija (finalno, stvaran output)

```text
$ python -m pytest tests/ -q
336 passed, 11 warnings in 18.24s

$ ruff check src/dentaland desktop backend tests
All checks passed!

$ mypy src/dentaland desktop backend
Success: no issues found in 40 source files
```

## Dirnuti fajlovi (u ovoj rundi)

```text
M  tests/test_ref03_booking_split.py   (denylist → allowlist)
A  agent_reports/2026-08-24-REF-03-f1-allowlist.md
```

`booking.py` vraćen na čisto (`git restore`) nakon svake mutacije — nije dio
diff-a; produkcija nedirnuta.
