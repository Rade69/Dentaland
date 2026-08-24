---
task_id: REF-02
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: IMPLEMENTATION_COMPLETE (popravka nakon Codex REJECT)
created_at: 2026-08-24
---

# REF-02 — popravka po Codexovom REJECT-u (F1 + F2)

## Šta je popravljeno

### F1 — eager-load test sada razlikuje eager od lazy

`test_range_eager_load_konstantan_broj_upita` više ne koristi 1 doktor + 1
servis. Sada seeduje **4 doktora + 6 servisa** i 12 termina raspoređenih
preko oba skupa (`doctor_id=i%4`, `service_id=i%6`). Lazy varijanta bi
radila `1 + 4 + 6 = 11` upita, eager `1 + 2 = 3`; prag `<= 5` stvarno
razdvaja ta dva slučaja.

### F2 — adjacency testovi za oba ruba half-open intervala

Dodata dva nova testa:

- `test_range_start_na_granici_kraja_se_ne_ukljucuje` — `start_time ==
  range_end` (18:00) se ne uključuje.
- `test_range_end_na_granici_pocetka_se_ne_ukljucuje` — `end_time ==
  range_start` (17:00) se ne uključuje.

## Adversarne provjere (stvaran tool output)

### F1 — uklonjena oba `selectinload` poziva

```text
python -m pytest tests/test_ref02_range_reads.py::test_range_eager_load_konstantan_broj_upita -q

E       AssertionError: očekivano <=5 upita, dobijeno 11
E       assert 11 <= 5
FAILED tests/test_ref02_range_reads.py::test_range_eager_load_konstantan_broj_upita
1 failed in 0.46s
```

Poslije vraćanja (`git checkout -- src/dentaland/services/booking.py`):

```text
1 passed in 0.38s
```

### F2 — promijenjeno `<` u `<=` i `>` u `>=`

```text
python -m pytest tests/test_ref02_range_reads.py::test_range_start_na_granici_kraja_se_ne_ukljucuje \
                    tests/test_ref02_range_reads.py::test_range_end_na_granici_pocetka_se_ne_ukljucuje -q

FAILED tests/test_ref02_range_reads.py::test_range_start_na_granici_kraja_se_ne_ukljucuje
FAILED tests/test_ref02_range_reads.py::test_range_end_na_granici_pocetka_se_ne_ukljucuje
2 failed in 0.47s
```

Poslije vraćanja: 8/8 testova u fajlu prolazi.

## Verifikacija

```text
pytest tests/ -q
→ 330 passed, 11 warnings   (328 + 2 nova adjacency testa)

ruff check src/dentaland desktop backend tests
→ All checks passed!, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 38 source files
```

## Changed files

- `tests/test_ref02_range_reads.py` — F1 seed (4 doktora + 6 servisa) + 2
  nova adjacency testa.

Produkcijski kod (`booking.py`, `day_view.py`, `week_view.py`) NIJE mijenjan
u ovoj popravci — samo test fajl.

## Handoff

CILJ: testovi zaista padaju kad se pokvare invarijante koje štite.

URAĐENO: F1 sada deterministički razlikuje eager (3) od lazy (11) upita; F2
zaključava half-open granice. Oba adversarno dokazana (F1 padne bez
selectinload, F2 padne sa `<=`/`>=`), pa vraćena na zeleno.

NE DIRATI: produkcijsku implementaciju (nema novih nalaza).

SLJEDEĆE: Codex ponavlja oba mutaciona testa na ispravljenoj verziji, pa
Claude review, pa Radovan human approval.
