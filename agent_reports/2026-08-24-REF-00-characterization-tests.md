---
task_id: REF-00
risk: LOW/MEDIUM
implementer: pi
reviewers: [codex, claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-24
---

# REF-00 — Arhitektonska sigurnosna mreža (characterization testovi)

## Task Contract

Izvor: `agent_reports/REF-00-task-contract.md` (napisan PRIJE koda). Cilj:
zaključati trenutno ponašanje prije REF-01..08. Risk LOW/MEDIUM; dva
obavezna reviewera (Codex pa Claude), Radovan human approval prije merge-a.

## Šta je urađeno

1. **`docs/dentaland-ref00-characterization-map.md`** — mapa ključnih
   ponašanja → postojeći testovi (12 workflow-a), identifikovana mjesta gdje
   postojeći testovi diraju implementacijski detalj (HTML font-size, status
   simboli, geometrijski `width()/sizeHint()`, privatni `_status_key` import
   u `day_view.py`), i opis novih REF-00 testova.
2. **`tests/test_ref00_overlap_error_contract.py`** (10 testova) — baseline
   za DVIJE odvojene `OverlapError` klase (dodatni zadatak iz review-a):
   - `booking.OverlapError` ≠ `requests.OverlapError`;
   - `dentaland.services.OverlapError` re-eksportuje `booking` klasu;
   - `backend.main.OverlapError` je `requests` klasa;
   - desktop `main_window`/`day_view`/`week_view`/`blockout_panel` hvataju
     `booking` klasu, a `requests_panel` hvata `requests` klasu;
   - behavior: `AppointmentService.create` baca `booking` klasu,
     `confirm_request` baca `requests` klasu (sa `type(...) is ...`
     provjerama, ne samo `pytest.raises`).
3. **`tests/test_ref00_service_api_contract.py`** (9 testova) — javni API
   surface za REF-03: imena javnih metoda `AppointmentService`, polja svih
   javnih DTO-ova, `dentaland.services.__all__` re-eksport, `AppointmentStatus`
   enum vrijednosti. Samo JAVNI simboli — privatne metode (`_check_overlap`,
   `_to_dto`, ...) NISU zaključane.

## Changed files (sve u allowed_paths, nijedan produkcioni fajl)

- `tests/test_ref00_overlap_error_contract.py` — novi (10 testova).
- `tests/test_ref00_service_api_contract.py` — novi (9 testova).
- `docs/dentaland-ref00-characterization-map.md` — nova mapa.
- `agent_reports/REF-00-task-contract.md` — Task Contract.
- `agent_reports/2026-08-24-REF-00-characterization-tests.md` — ovaj izvještaj.

`desktop/**`, `src/dentaland/**`, `backend/**`, `migrations/**` — NIJEDAN
produkcioni fajl nije diran (potvrđeno `git status`).

## Verifikacija (rezultati)

```text
pytest tests/ -q
→ 317 passed, 11 warnings   (298 baseline + 19 novih REF-00 testova)

ruff check src/dentaland desktop backend tests
→ All checks passed!, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 37 source files
```

Warnings su postojeći dependency deprecation warning-i (httpx/slowapi/
alembic), ne vezani za ovaj task.

## Kako novi testovi padaju kad se invariant pokvari (za Codex review)

- Ako REF-01 objedini `OverlapError` tako da `backend.main` počne hvatati
  `booking` klasu umjesto `requests` klase →
  `test_backend_main_hvata_requests_klasu` pada (`is` identitet, ne ime).
- Ako se `dentaland.services` re-eksport prebaci sa `booking` na `requests`
  klasu → `test_services_reexport_je_booking_klasa` pada.
- Ako se `confirm_request` promijeni da baca `booking` klasu →
  `test_confirm_request_baca_requests_klasu` pada (behavior + `type() is`).
- Ako REF-03 izgubi/renomira javnu metodu ili DTO polje →
  `test_ref00_service_api_contract.py` pada.

Svi novi testovi koriste determinističke `is`/sadržaj/state provjere — nijedan
se ne oslanja na `width()/sizeHint()` geometriju (FIX-03 presedan).

## Napomene za reviewere

- **Codex (test kvalitet):** behavior testovi (`test_service_create_baca_booking_klasu`,
  `test_confirm_request_baca_requests_klasu`) koriste `type(excinfo.value) is
  X` umjesto samo `pytest.raises(X)` — dokazuju tačnu klasu, ne samo
  podklasa/ime. Preporučujem adversarnu provjeru: privremeno zamijeniti
  `backend.main.OverlapError` sa `booking.OverlapError` i potvrditi da
  `test_backend_main_hvata_requests_klasu` padne.
- **Claude (arhitektura):** `test_ref00_service_api_contract.py` zaključava
  SAMO javne simbole; OverlapError testovi su mjera "šta se mijenja" (dokumentuju
  NAMJERNO privremeno stanje dve klase), ne zabrana da se u REF-01 objedini —
  mapi je to eksplicitno navedeno.

## Review

`PENDING` — implementer nije reviewer. Redoslijed: Codex prvi, pa Claude.
Radovan human approval obavezan prije merge-a.

## Integration status

`NOT_MERGED` — čeka dva review-a.

## Handoff

CILJ: sigurnosna mreža (mapa + nedostajući testovi) prije REF-01..08.

URAĐENO: mapa ponašanja→testovi, OverlapError baseline (dve klase + catch
mapiranje + behavior), javni API contract testovi.

NE DIRATI: sav produkcioni kod (potvrđeno — nula izmjena).

SLJEDEĆE: Codex review (test kvalitet) → Claude review (arhitektura) →
Radovan human approval → merge.
