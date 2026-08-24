---
task_id: REF-03
risk: MEDIUM
reviewer: pi
reviewer_role: Reviewer 1 (nezavisna provjera F1 body-shape fixa)
reviewed_commit: d966200b335f8c1be4a7bcad9d63c99ec4555471
verdict: PASS
created_at: 2026-08-24
---

# REF-03 — nezavisna provjera F1 body-shape fixa

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## Standardna verifikacija (nezavisno ponovljena)

```text
git rev-parse HEAD  → d966200b335f8c1be4a7bcad9d63c99ec4555471

pytest tests/ -q  → 336 passed, 11 warnings (exit 0)
pytest tests/test_ref00_service_api_contract.py -q  → 9 passed (nepromijenjen)
ruff check src/dentaland desktop backend tests  → All checks passed!
mypy src/dentaland desktop backend  → Success: no issues found in 40 source files
```

## Mutacije — stvarni tool output (svaka u izolovanoj izmjeni + git checkout)

### M1 — state side effect prije delegacije

```python
def mark_arrived(self, appt_id):
    self.doctor_id = 999
    return appointments.mark_arrived(self._session_factory, appt_id)
```

```text
E  AssertionError: AppointmentService.mark_arrived mijenja state prije delegacije: self.doctor_id = 999
FAILED tests/test_ref03_booking_split.py::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
1 failed, 5 passed
```

### M2 — raw SQL u privatnoj metodi

```python
from sqlalchemy import text
def _raw_sql(self):
    session = self._session_factory()
    session.execute(text("SELECT * FROM appointments"))
```

```text
E  AssertionError: AppointmentService._raw_sql ima nedozvoljene pozive: ['self._session_factory()', "session.execute(text('SELECT * FROM appointments'))", "text('SELECT * FROM appointments')"]
E  AssertionError: AppointmentService ima neočekivanu privatnu metodu: _raw_sql
FAILED tests/test_ref03_booking_split.py::test_booking_facade_pozivi_su_samo_iz_allowlista
FAILED tests/test_ref03_booking_split.py::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
2 failed, 4 passed
```

### M3 — aliasirani import

```python
from sqlalchemy import select as sel
def _aliased(self):
    sel(Doctor).where(Doctor.ime == "x")
```

```text
E  AssertionError: AppointmentService._aliased ima nedozvoljene pozive: ["sel(Doctor).where(Doctor.ime == 'x')", 'sel(Doctor)']
E  AssertionError: AppointmentService ima neočekivanu privatnu metodu: _aliased
FAILED ...::test_booking_facade_pozivi_su_samo_iz_allowlista
FAILED ...::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
2 failed, 4 passed
```

### M4 — dinamički getattr

```python
def _dynamic(self):
    session = self._session_factory()
    execute = getattr(session, "execute")
    execute("SELECT * FROM appointments")
```

```text
E  AssertionError: AppointmentService._dynamic ima nedozvoljene pozive: ['self._session_factory()', "getattr(session, 'execute')", "execute('SELECT * FROM appointments')"]
E  AssertionError: AppointmentService ima neočekivanu privatnu metodu: _dynamic
FAILED ...::test_booking_facade_pozivi_su_samo_iz_allowlista
FAILED ...::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
2 failed, 4 passed
```

## Nove probe (peta rupa i dalje)

### P1 — dva legitimna delegacijska poziva zaredom

```python
def mark_arrived(self, appt_id):
    appointments.mark_arrived(self._session_factory, appt_id)
    return appointments.mark_arrived(self._session_factory, appt_id)
```

```text
E  AssertionError: AppointmentService.mark_arrived ima nedozvoljenu naredbu prije delegacije: appointments.mark_arrived(self._session_factory, appt_id)
FAILED ...::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
FAILED ...::test_facade_metoda_delegira
2 failed, 4 passed
```

"Tačno jedan" zaista znači jedan.

### P2 — sumnjiva logika unutar argumenta (tuple index)

```python
return appointments.mark_arrived(self._session_factory, (999, appt_id)[1])
```

```text
E  AssertionError: AppointmentService.mark_arrived ima izračunavanje/sporedni efekat u argumentima delegacije: ['(999, appt_id)[1]']
FAILED ...::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
1 failed, 5 passed
```

### P3 — walrus u argumentu

```python
return appointments.mark_arrived(self._session_factory, (x := appt_id))
```

```text
E  AssertionError: AppointmentService.mark_arrived ima izračunavanje/sporedni efekat u argumentima delegacije: ['(x := appt_id)']
FAILED ...::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
1 failed, 5 passed
```

AST stvarno hvata `NamedExpr` — ne samo u opisu.

### P4 — lambda kao argument

```python
return appointments.mark_arrived(self._session_factory, lambda: appt_id)
```

```text
E  AssertionError: AppointmentService.mark_arrived ima izračunavanje/sporedni efekat u argumentima delegacije: ['lambda: appt_id']
FAILED ...::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
FAILED ...::test_facade_metoda_delegira
2 failed, 4 passed
```

### P5 — test iterira SVE javne metode (ne fiksnu listu)

Dodata nova javna metoda `new_public_method(self): self.doctor_id = 5`:

```text
E  AssertionError: AppointmentService.new_public_method ne završava čistom delegacijom: self.doctor_id = 5
FAILED ...::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
1 failed, 5 passed
```

Test čita klase iz `ast.parse` source-a (`_appointment_service_methods()` vraća
SVE `FunctionDef` u `AppointmentService`), pa svaka buduća javna metoda pada
automatski pod istu provjeru — nema fiksne liste imena.

### P6 — bezazlena privatna metoda

```python
def _helper(self):
    return 1
```

```text
E  AssertionError: AppointmentService ima neočekivanu privatnu metodu: _helper
FAILED ...::test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik
1 failed, 5 passed
```

## Non-blocking nalaz (za Claude Reviewer 2)

Test odbija **BAŠ SVAKU** privatnu metodu na `AppointmentService`, osim
eksplicitno izuzete `_require_doctor` — uključujući bezazlene privatne
helper-e bez ikakvog data-access poziva (P6). Ovo NIJE lažni PASS (test
ispravno hvata više, ne manje), ali je strožije od "bez SQL-a u facade-u":
legitiman budući privatni helper (npr. čisto formatiranje) bi pao. Da li je
ta strogoća namjerna arhitektonska odluka ili treba razlikovati "privatna
metoda sa data-access" od "bezazlena privatna metoda" — arhitektonski sud za
Claude-a, ne blokira test kvalitet.

## Zaključak

`verdict: PASS`. Granica je robusna jer je provjera strukturna allowlist
(default "odbij") nad kompletnim AST tijelom, ne string-match: sve četiri
izvorne mutacije + pet novih proba daju stvaran FAIL, a test iterira cijelu
klasu pa ne može "zaboraviti" novu metodu. Jedina nijansa (P6) je
prestrogost za privatne metode, proslijeđena Claude-u kao arhitektonska
napomena — ne utiče na to da test stvarno štiti ono što tvrdi da štiti.
