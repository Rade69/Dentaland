---
task_id: REF-02
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
reviewer: codex
verdict: REJECT
commits: [df88ae3]
created_at: 2026-08-24
---

# REF-02 — Codex review (test kvalitet)

```yaml
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
blocking_findings:
  - "F1 tests/test_ref02_range_reads.py:155-192 — eager-load test koristi samo jednog doktora i jedan servis; nakon potpunog uklanjanja oba selectinload poziva test i dalje prolazi (1 passed), pa ne dokazuje konstantan broj upita niti štiti N+1 invariant."
  - "F2 tests/test_ref02_range_reads.py:84-128 — nema termina koji tačno dodiruje range granicu; nakon promjene start_time < range_end u start_time <= range_end sva tri relevantna range testa i dalje prolaze (3 passed), pa half-open overlap contract nije zaključan."
```

## Zaključak

Produkcijska implementacija izgleda konzistentno sa Task Contractom, puni
gate-ovi su zeleni i scope je čist. Review je ipak `REJECT` jer dva nova
testa ne padaju kada se pokvare invarijante koje tvrde da štite.

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

## Adversarne provjere

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

URAĐENO: REJECT — produkcijski gate-ovi prolaze, ali F1 i F2 daju
adversarni lažni PASS.

NE DIRATI: produkcijsku implementaciju bez novog nalaza; trenutni blocking
nalazi su ograničeni na kvalitet `tests/test_ref02_range_reads.py`.

SLJEDEĆE: Pi dopunjava F1 fixture različitim relationship entitetima i F2
adjacency slučajevima; Codex ponavlja oba mutaciona testa. Claude review ide
tek poslije Codex PASS re-review-a, zatim Radovan human approval.
