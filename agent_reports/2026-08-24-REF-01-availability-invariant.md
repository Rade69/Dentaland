---
task_id: REF-01
risk: MEDIUM
implementer: crush
reviewers: [codex, claude]
verdict: PENDING
commits: [d8bfe99]
created_at: 2026-08-24
---

# REF-01 — Availability invariant (jedan source of truth za overlap)

## Task Contract

Pun Task Contract je u zadatku (`paste_1.txt`). Suština:

- Novi modul `src/dentaland/services/availability.py` — `OverlapError` +
  `validate_appointment_overlap(session, doctor_id, start, end, exclude_id=None)`.
- Ukida dupliranu overlap logiku (`booking._check_overlap` i `requests._check_overlap`).
- **Kritičan nalaz riješen:** dvije istoimene `OverlapError` klase
  (`booking` vs `requests`) → kanonizovane u jednu u `availability.py`.

## Šta je urađeno

- `src/dentaland/services/availability.py` (novo) — kanonična `OverlapError`
  + `validate_appointment_overlap` (jedini overlap query, sa `exclude_id`).
- `booking.py` — `OverlapError` re-eksportovan (import iz availability,
  class definicija uklonjena); `_check_overlap` delegira na
  `validate_appointment_overlap`. `_check_timeoff_overlap` (blokada) ostaje
  lokalno (druga iteracija, druga poruka).
- `requests.py` — `OverlapError` re-eksportovan; `_check_overlap` (SQL kopija)
  UKLONJENA; `confirm_request` direktno koristi `validate_appointment_overlap`.
- `backend/main.py` — `OverlapError` importovan iz `availability` (umjesto
  `requests`), catch klauzula na 172 i dalje vraća 409.
- `tests/test_availability.py` (novo) — kanonizacija klase + overlap invariant.

## OverlapError kanonizacija (kritičan nalaz)

- `availability.OverlapError` **is** `booking.OverlapError` **is**
  `requests.OverlapError` **is** `dentaland.services.OverlapError`
  (dokazano `test_overlap_error_je_jedna_kanonicka_klasa`).
- Desktop (preko `dentaland.services.OverlapError`) i backend (preko
  `availability.OverlapError`) sada hvataju ISTU klasu.
- `create`/`move`/`confirm_request` dijele istu provjeru i isti tip greške.

## REF-00 merge + tačne izmjene testova

REF-00 je merge-ovan u `main` (nakon početka rada), pa je urađen
`git merge origin/main` (fast-forward) i onda su SVJESNO ažurirani
REF-00 testovi koji su zaključavali staro stanje (dvije klase). Tačno:

`tests/test_ref00_overlap_error_contract.py`:

| Prije (REF-00) | Poslije (REF-01) | Zašto |
|---|---|---|
| `test_dve_klase_istog_imena_su_razlicite`: `assert BookingOverlapError is not RequestsOverlapError` | `test_overlap_error_je_jedna_kanonicka_klasa`: `assert BookingOverlapError is RequestsOverlapError` | REF-01 kanonizuje klase — obrnut smisao |
| `test_services_reexport_je_booking_klasa`: `assert ServicesOverlapError is not RequestsOverlapError` | `test_services_reexport_je_kanonicka_klasa`: `assert ServicesOverlapError is RequestsOverlapError` | re-eksport sada vodi na istu kanoničnu klasu |
| `test_backend_main_hvata_requests_klasu`: `assert backend_main.OverlapError is not BookingOverlapError` | `test_backend_main_hvata_kanonicku_klasu`: `assert backend_main.OverlapError is BookingOverlapError` | backend i desktop hvataju istu klasu |
| `test_service_create_baca_booking_klasu`: `assert type(...) is not RequestsOverlapError` | `test_service_create_baca_kanonicku_klasu`: `assert type(...) is RequestsOverlapError` | create baca kanoničnu klasu |
| `test_confirm_request_baca_requests_klasu`: `assert type(...) is not BookingOverlapError` | `test_confirm_request_baca_kanonicku_klasu`: `assert type(...) is BookingOverlapError` | confirm baca kanoničnu klasu |

Nijedan test nije izbrisan — svaki je preformulisan da genuinski hvata
regresiju: ako neko vrati dvije odvojene klase, `is` asercije padaju.

## Verifikacija

| Komanda | Rezultat |
|---|---|
| `pytest tests/ -q` | 322 passed |
| `ruff check src/dentaland desktop backend tests` | All checks passed |
| `mypy src/dentaland desktop backend` | Success (0 grešaka) |

322 = REF-00 baseline (317) + `tests/test_availability.py` (5 novih);
nijedan slučaj nije izgubljen (samo preformulisan).

## Review

PENDING — čeka Codex (test kvalitet) pa Claude (arhitektura), zatim human
approval.

## Integration status

NOT_MERGED — čeka review i human approval (Codex prvi).
