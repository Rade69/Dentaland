---
task_id: REF-00
risk: LOW/MEDIUM
implementer: pi
reviewers: [codex, claude]
reviewer: codex
verdict: PASS
commits: [3bbbca1]
created_at: 2026-08-24
---

# REF-00 — Codex review (test kvalitet)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## Nezavisni zaključak

Novi characterization testovi stvarno reaguju na tražene povrede
invarijanti. Provjera nije zasnovana na implementer izvještaju: ponovljeni su
puni gate-ovi, pregledan je stvarni diff i izvršene su tri izolovane
adversarne mutacije nad kopijom commita `3bbbca1`.

## Scope

`git diff --stat 3621cfa..3bbbca1` pokazuje pet novih fajlova i 613 umetnutih
linija:

- `tests/test_ref00_overlap_error_contract.py`
- `tests/test_ref00_service_api_contract.py`
- `docs/dentaland-ref00-characterization-map.md`
- `agent_reports/REF-00-task-contract.md`
- `agent_reports/2026-08-24-REF-00-characterization-tests.md`

Nema izmjena u `desktop/**`, `src/dentaland/**`, `backend/**` ni
`migrations/**`. `git diff --check 3621cfa..3bbbca1` je čist.

## Verifikacija

Pokrenuto u worktree-u `REF-00-characterization-tests`:

```text
pytest tests/ -q
317 passed, 11 warnings in 16.76s (exit 0)

ruff check src/dentaland desktop backend tests
All checks passed! (exit 0)

mypy src/dentaland desktop backend
Success: no issues found in 37 source files (exit 0)
```

Warnings su dependency deprecation upozorenja iz Starlette/slowapi/Alembic
putanja; nisu novi REF-00 test failure-i.

## Adversarna provjera

Mutacije su rađene u izolovanoj privremenoj kopiji i zatim uklonjene; nijedan
produkcijski fajl u grani nije mijenjan.

1. `backend/main.py` je privremeno promijenjen da uvozi i hvata
   `booking.OverlapError` umjesto `requests.OverlapError`.
   `test_backend_main_hvata_requests_klasu` je genuinski pao:
   `AssertionError: booking.OverlapError is RequestsOverlapError`.
2. Javno polje `AppointmentDTO.patient_name` privremeno je preimenovano u
   `patient_full_name`. `test_appointment_dto_polja` je genuinski pao i
   prijavio tačno dodatno/nedostajuće polje.
3. Privatna metoda `_check_overlap` i njeni interni pozivi dosljedno su
   preimenovani u `_check_schedule_overlap`. Cijeli
   `tests/test_ref00_service_api_contract.py` ostao je zelen: `9 passed`.
   Time je dokazano da API-contract test ne zaključava tu privatnu metodu.

Behavior testovi za oba izvora overlap greške koriste
`type(excinfo.value) is X` i dodatnu negativnu identity provjeru. Zato bi
nasljeđivanje jedne klase iz druge i dalje bilo razlikovano; test se ne
oslanja samo na `pytest.raises()`/`isinstance()`.

## Characterization mapa

Mapa ima svih 12 stavki iz Task Contracta:

1. create appointment;
2. edit;
3. move;
4. cancel;
5. delete;
6. status transitions;
7. web request confirm/reject;
8. Day/Week switch;
9. doctor filter;
10. TimeOff/block rendering;
11. print action;
12. status summary.

`pytest --collect-only` i ciljani `rg` spot-check potvrđuju da navedeni
testovi/fajlovi postoje za servisne create/edit/move/cancel/delete/status
tokove, backend confirm/reject, Day/Week, filter doktora, block rendering,
print i status summary. Mapa takođe odvojeno označava postojeće testove koji
diraju geometriju, HTML/simbole i privatni `_status_key`, umjesto da ih
predstavlja kao poželjan javni contract.

## Napomena za Reviewer 2

Ovaj PASS potvrđuje kvalitet i osjetljivost testova. Claude ostaje Reviewer 2
za arhitektonsku procjenu da li je izabrani javni surface ispravan dugoročni
contract. Radovan human approval i merge ne smiju prethoditi tom review-u.

## Handoff

CILJ: nezavisno dokazati da REF-00 testovi stvarno padaju kada se ugovoreni
invariant pokvari i da mapa pokriva svih 12 workflow-a.

URAĐENO: PASS — puni gate-ovi su zeleni, scope je čist, obje javne mutacije
daju očekivani FAIL, a privatno preimenovanje ostavlja API-contract testove
zelenim.

NE DIRATI: produkcijski kod i REF-01 implementaciju; privremene adversarne
kopije su uklonjene.

SLJEDEĆE: Claude radi Reviewer 2 arhitektonski review, zatim Radovan daje ili
uskraćuje human approval; tek potom je dozvoljen merge.
