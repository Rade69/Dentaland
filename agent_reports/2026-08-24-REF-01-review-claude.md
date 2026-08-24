---
task_id: REF-01
risk: MEDIUM
reviewer: claude
implementer: crush
reviewer_role: Reviewer 2 (arhitektura)
verdict: PASS
commits: [83dfbc9]
created_at: 2026-08-24
---

# REF-01 — Claude review (arhitektura, Reviewer 2)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

```text
CILJ: Nezavisno provjeriti da je availability.py ispravno postao source of
      truth za overlap invarijantu, da facade (AppointmentService) ostaje
      čist, i da je desktop netaknut.
URAĐENO: PASS — potvrđeno vlastitim čitanjem svakog izmijenjenog fajla i
      diff-a, ne implementerovim izvještajem. Jedna non-blocking napomena
      o nekonzistentnom stilu u novom test fajlu.
NE DIRATI: desktop/**, models.py, migrations/** — nedirano, potvrđeno.
SLJEDEĆE: Ovaj review je urađen PRIJE Codexovog (na eksplicitan zahtjev
      Radovana, van uobičajenog redoslijeda) — Codexov test-kvalitet
      review i dalje treba da se odradi prije human approval-a i merge-a.
```

## Napomena o redoslijedu

Task Contract za REF-01 (kao i REF-00) traži "Codex prvi, pa Claude".
Ovaj review je urađen prije Codexovog na eksplicitan zahtjev Radovana.
Ovo NE zamjenjuje Codexov test-kvalitet review — samo ide paralelno/prije
njega. Human approval i merge i dalje čekaju oba reviewa.

## 0. Preduslov — sinhronizacija sa main-om (već riješeno, ovdje samo potvrđeno)

Prvi pokušaj Crush-a je bio na zastarjeloj osnovi (bez REF-00 sigurnosne
mreže). Nakon eksplicitnog zahtjeva za sinhronizaciju, grana je ažurirana:

```text
git merge-base --is-ancestor edd7cbc HEAD → potvrđeno (main HEAD JE predak)
```

## 1. Scope

```text
git diff --stat edd7cbc..83dfbc9
→ backend/main.py, src/dentaland/services/{availability.py (novo),
  booking.py, requests.py}, tests/{test_availability.py (novo),
  test_ref00_overlap_error_contract.py}, agent_reports/**
```

Nema izmjena u `desktop/**`, `src/dentaland/models.py`, `migrations/**` —
potvrđeno, u skladu sa Task Contract forbidden_paths. `scope: PASS`.

## 2. Nezavisna verifikacija (ponovljena, ne prepisana)

```text
pytest tests/ -q                              → 322 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 38 source files
```

## 3. Arhitektura — da li je availability.py ispravan source of truth

Pročitao sam `availability.py` u cjelini (54 linije) — minimalan,
fokusiran modul: jedna klasa (`OverlapError`), jedna funkcija
(`validate_appointment_overlap`). Nema uvoza `booking.py`/`requests.py` —
nalazi se na dnu zavisnosti, oba servisna fajla zavise OD njega, ne
obrnuto. **Nema kružnog uvoza**: `requests.py` uvozi samo iz
`availability.py` (ne iz `booking.py`); `booking.py` uvozi i iz
`availability.py` i iz `requests.py` (za `RequestDTO`/`confirm_request`,
postojeći facade odnos od prije REF-01, nepromijenjen). Dependency graf
ostaje acikličan.

`AppointmentService._check_overlap` (u `booking.py`) je svedena na
jednorediju delegaciju:

```python
def _check_overlap(self, ..., exclude_id=None):
    validate_appointment_overlap(session, doctor_id, start, end, exclude_id=exclude_id)
```

Ovo je tačno onaj "facade ostaje tanak sloj" obrazac koji plan traži —
nema poslovne logike duplirane u facade-u, samo delegacija.

`requests.py::confirm_request` sada direktno poziva
`validate_appointment_overlap` (bez posredne `_check_overlap` funkcije —
implementer ju je potpuno uklonio, ne samo delegirao). Ovo je čistije od
onoga što je Task Contract tražio (delegacija) — direktno uklanjanje
nepotrebnog sloja indirekcije je opravdano jer `requests.py` više nema
sopstvenu overlap logiku koju bi trebalo omotati.

## 4. Facade i re-eksport lanac — provjeren ručno, simbol po simbol

`src/dentaland/services/__init__.py` NIJE mijenjan (nema diff-a) — i dalje
uvozi `OverlapError` iz `booking.py`. Pošto `booking.py` sada uvozi
`OverlapError` iz `availability.py` na vrhu fajla (umjesto da je
definiše), lanac `dentaland.services.OverlapError` → `booking.OverlapError`
→ `availability.OverlapError` ostaje ista, kanonična klasa. Postojeći
GUI kod koji uvozi `from dentaland.services import OverlapError` nastavlja
da radi bez izmjene uvozne putanje — backward-compat obećanje iz Task
Contracta je ispunjeno doslovno, ne samo funkcionalno.

`backend/main.py` diff je minimalan (2 linije) — samo promijenjena
uvozna putanja `OverlapError`-a sa `requests` na `availability`; `except
OverlapError` catch klauzula na liniji 172 nedirnuta.

## 5. Desktop — potvrđeno netaknut

`git diff --stat` ne pokazuje ništa u `desktop/**`. Testovi u
`test_ref00_overlap_error_contract.py` koji provjeravaju da desktop
view-ovi (main_window/day_view/week_view/blockout_panel/requests_panel)
hvataju ispravnu klasu su NEDIRNUTI (implementer ih nije morao mijenjati
jer je re-eksport lanac ostao stabilan) — ovo je samo po sebi dokaz da je
desktop netaknut na funkcionalnom nivou, ne samo da fajlovi nisu editovani.

## 6. REF-00 test izmjene — pregledane liniju po liniju

Pregledao sam kompletan diff `tests/test_ref00_overlap_error_contract.py`
(ne samo tabelu iz izvještaja). Svih pet `is not` → `is` obrtanja su
semantički ispravna i odgovaraju stvarnoj novoj arhitekturi:

- `test_dve_klase_istog_imena_su_razlicite` → `test_overlap_error_je_jedna_kanonicka_klasa`
- `test_services_reexport_je_booking_klasa` → `test_services_reexport_je_kanonicka_klasa`
- `test_backend_main_hvata_requests_klasu` → `test_backend_main_hvata_kanonicku_klasu`
- `test_service_create_baca_booking_klasu` → `test_service_create_baca_kanonicku_klasu`
- `test_confirm_request_baca_requests_klasu` → `test_confirm_request_baca_kanonicku_klasu`

Docstring modula je ažuriran da opisuje NOVO stanje umjesto starog. Nazivi
testova su promijenjeni da odražavaju novi smisao (ne samo asercija
promijenjena uz staro ime, što bi bilo zbunjujuće).

## 7. Non-blocking napomena — nekonzistentan stil u novom testu

`tests/test_availability.py:117`:

```python
status=Appointment.__mapper__.c.status.type.python_type.SCHEDULED,
```

Ovo je nepotrebno komplikovan način pisanja `AppointmentStatus.SCHEDULED`
— ide kroz SQLAlchemy mapper introspekciju da bi došao do istog enuma
koji se već uvozi na vrhu fajla i koristi direktno na linijama 82 i 100 u
ISTOM fajlu (`status=AppointmentStatus.SCHEDULED`). Radi ispravno (testovi
prolaze), ali je nekonzistentno i nepotrebno teže za čitanje. Ne blokira
PASS — vrijedi pojednostaviti u prolazu, nije vrijedno posebnog commita.

## Zaključak

PASS. `availability.py` je ispravan, minimalan source of truth bez
kružnih zavisnosti. Facade (`AppointmentService._check_overlap`) je sveden
na čistu delegaciju. Re-eksport lanac čuva backward-compat import putanje
za postojeći GUI kod. Desktop je netaknut i funkcionalno (ne samo
tekstualno). REF-00 test izmjene su semantički ispravne, ne mehaničko
prepravljanje. Jedna non-blocking stilska napomena, ne zahtijeva izmjenu
prije merge-a. I dalje čekamo Codexov test-kvalitet review prije human
approval-a.
