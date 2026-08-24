---
task_id: REF-02
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
reviewer: codex
verdict: PASS
commits: [df88ae3, 730081b]
created_at: 2026-08-24
---

# REF-02 — Codex review (test kvalitet)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## Finalni zaključak — re-review runda 2

Pi je u commitu `730081b` zatvorio oba nalaza iz prve runde. Ponovljene
mutacije sada daju očekivani FAIL, puni gate-ovi su zeleni i produkcijski kod
nije mijenjan. Finalni Codex verdikt je `PASS`.

### Runda 2 — verifikacija

```text
pytest tests/ -q
330 passed, 11 warnings in 11.11s (exit 0)

ruff check src/dentaland desktop backend tests
All checks passed! (exit 0)

mypy src/dentaland desktop backend
Success: no issues found in 38 source files (exit 0)
```

Fix diff `3e126b9..730081b` sadrži samo
`tests/test_ref02_range_reads.py` i novi `agent_reports/**` izvještaj.

### F1 zatvoren

Nakon ponovnog uklanjanja oba `selectinload` poziva:

```text
test_range_eager_load_konstantan_broj_upita
FAILED: očekivano <=5 upita, dobijeno 11
```

Fixture sa 4 doktora i 6 servisa sada deterministički razlikuje lazy
varijantu (11 upita) od eager varijante (3 upita).

### F2 zatvoren

Mutacija `Appointment.start_time < range_end` u `<=` ruši
`test_range_start_na_granici_kraja_se_ne_ukljucuje`: termin na desnoj
granici pogrešno se vraća. Odvojena mutacija `Appointment.end_time >
range_start` u `>=` ruši
`test_range_end_na_granici_pocetka_se_ne_ukljucuje`. Obje half-open granice
su sada stvarno zaključane.

## Scope

`git diff --stat 4e45212..df88ae3` pokazuje samo:

- `src/dentaland/services/booking.py`;
- `desktop/views/day_view.py`;
- `desktop/views/week_view.py`;
- `tests/test_ref02_range_reads.py`;
- dva REF-02 fajla u `agent_reports/**`.

Nisu dirnuti `print_schedule.py`, `availability.py`, `requests.py`,
`main_window.py`, `models.py` ni `migrations/**`. `all_combined()` i njegov
poziv iz print servisa ostali su netaknuti.

Remote precondition je provjeren prije review-a. Grana prvobitno nije
postojala na `origin`; postojeći implementer commit je zatim pušovan i
potvrđen kao `df88ae39a5e92245c4d620ebe654c89ae615c696`.

## Verifikacija

```text
pytest tests/ -q
328 passed, 11 warnings in 11.36s (exit 0)

ruff check src/dentaland desktop backend tests
All checks passed! (exit 0)

mypy src/dentaland desktop backend
Success: no issues found in 38 source files (exit 0)
```

## Adversarne provjere — runda 1 (istorija nalaza)

### F1 — eager-load test daje lažan PASS

U izolovanoj kopiji commita uklonjena su oba poziva:

```python
selectinload(Appointment.doctor)
selectinload(Appointment.service)
```

Stvarni rezultat:

```text
pytest tests/test_ref02_range_reads.py::test_range_eager_load_konstantan_broj_upita -q
1 passed in 0.46s
```

Uzrok je upravo identity map ponašanje opisano u implementer izvještaju.
Test seeduje 30 termina, ali svi koriste isti doktor i isti servis. Lazy
varijanta zato radi jedan glavni SELECT + jedan doctor SELECT + jedan service
SELECT, što prolazi uslov `query_count <= 5`.

Test treba koristiti dovoljno različitih doktora i/ili servisa da lazy
varijanta deterministički pređe prag, dok eager varijanta ostaje na tri
upita. Minimalni fixture je dovoljan; nije potrebno praviti 5000 termina u
samom testu.

### F2 — half-open granice nisu testirane

U izolovanoj kopiji promijenjeno je:

```python
Appointment.start_time < range_end
```

u:

```python
Appointment.start_time <= range_end
```

Stvarni rezultat za osnovni, preko-ponoći i preko-kraja-sedmice test:

```text
3 passed in 0.40s
```

Postojeći komentari tačno opisuju termine koji stvarno preklapaju period,
ali nijedan fixture nema termin čiji je `start_time == range_end` ili čiji je
`end_time == range_start`. Potrebne su obje adjacency provjere koje dokazuju
da dodir bez preklapanja nije uključen.

## Nezavisno mjerenje

Sa novom memorijskom bazom, 5000 sintetičkih termina, 3 doktora i 100
servisa izmjereno je:

```text
all_combined():                    5000 redova, 104 SQL upita
appointments_for_range(1 dan):      48 redova,   3 SQL upita
```

Rezultat nezavisno potvrđuje formulu `1 + broj različitih doktora + broj
različitih servisa` za lazy varijantu i tri upita za `selectinload` varijantu.
Mutacija `<` u `<=` promijenila je jednodnevni rezultat sa 48 na 49 redova,
što dodatno potvrđuje da je F2 stvarna behavior razlika koju testovi trenutno
ne vide.

## Day/Week behavior

`day_view.py` je prije REF-02 već imao filter:

```python
appt.start.astimezone(SARAJEVO).date() == self.day
```

Diff ga nije uveo; samo je izvor podataka promijenjen sa `all_combined()` na
range read. Termin preko ponoći i dalje se prikazuje samo na dan početka,
što čuva prethodno GUI ponašanje.

`week_view.py::_cell_for()` računa kolonu iz lokalnog datuma početka i vraća
`None` kada je `col < 0` ili `col >= DAY_COUNT`. Zato termin koji range servis
vrati zbog preklapanja, ali počinje dan prije prikaza, neće biti pogrešno
pozicioniran. Ista render provjera je postojala prije REF-02 i ranije je
morala odbacivati termine iz cijele istorije; ovdje nema nove render
regresije.

## Handoff

CILJ: dokazati da REF-02 testovi štite range i eager-load invarijante prije
arhitektonskog review-a.

URAĐENO: PASS — F1 i F2 su zatvoreni; obje ponovljene mutacije daju
očekivani FAIL, a puni gate daje 330 passed.

NE DIRATI: produkcijsku implementaciju; re-review fix mijenja samo testove i
evidence izvještaj.

SLJEDEĆE: Claude radi Reviewer 2 arhitektonski review, zatim Radovan human
approval; merge tek poslije oba koraka.
