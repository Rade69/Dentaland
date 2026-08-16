---
task_id: DENT-007
risk: HIGH
implementer: claude
reviewers: []
verdict: APPROVED_WITHOUT_INDEPENDENT_REVIEW
commits: []
created_at: 2026-08-16
---

# DENT-007 — Lokalni FastAPI backend za javne zahtjeve

## Plan

Vidi `agent_reports/2026-08-16-DENT-007-plan.md`.

## Šta je urađeno

- `src/dentaland/models.py` — `AppointmentStatus` dobija `PENDING`/`REJECTED`
  (aditivno). `doctor_id`, `service_id`, `start_time`, `end_time` postaju
  nullable — nepoznati dok osoblje ne potvrdi zahtjev. Novo polje
  `requested_date` (datum koji je pacijent tražio na javnoj formi).
- `migrations/versions/b2c3d4e5f6a7_pending_requests.py` — batch-mode
  migracija (SQLite ne podržava direktan ALTER COLUMN), redefiniše CHECK
  constraint na `status` da uključi nove vrijednosti, upgrade i downgrade.
- `src/dentaland/services/requests.py` — `RequestDTO`, `create_request`,
  `list_pending`, `confirm_request` (dodjeljuje doktora/uslugu/vrijeme,
  računa `end_time` iz `Service.trajanje_min`, provjerava preklapanje),
  `reject_request`. Namjerno odvojen od `booking.py` (DENT-006 aktivno tamo)
  — overlap-check logika je duplirana kao mala samostalna funkcija.
- `backend/main.py` — FastAPI app: `POST /api/booking-requests` (javni,
  rate-limited 10/min), `GET /api/booking-requests` (lista PENDING),
  `POST /api/booking-requests/{id}/confirm` (409 na preklapanje, 404 na
  nepostojeći/već-obrađen), `POST /api/booking-requests/{id}/reject`.
  CORS otvoren za lokalno testiranje. Session factory kroz FastAPI
  dependency injection (testabilno, bez side-effecta na import).
- `web/app.js` — submit handler sada šalje pravi `fetch()` POST na
  `http://127.0.0.1:8000`, sa error porukom (inline stil, ne dira
  `styles.css`) umjesto lažnog client-side prelaska na korak 3.
- `pyproject.toml` — `fastapi`, `uvicorn`, `slowapi` (+ `httpx` u dev).
- `tests/test_requests.py` (10), `tests/test_backend.py` (9, uključujući
  stvaran rate-limit test — 11. zahtjev u minuti vraća 429).

## Verifikacija (stvarni rezultati)

| Komanda | Rezultat |
|---|---|
| `pytest tests/ -q` | 62 passed |
| `ruff check src/dentaland backend tests migrations` | All checks passed |
| `mypy src/dentaland backend` | 0 grešaka u mojim fajlovima (5 u `booking.py`, vidi napomenu ispod) |
| Stvaran uvicorn server (ne samo `TestClient`) + `httpx` POST/GET/OPTIONS | POST 201, GET 200, CORS preflight 200 sa `Origin: null` (potvrđuje da `web/index.html` otvoren kao fajl može stvarno pozvati backend) |

## Napomena — mypy regresija u tuđem fajlu (ne ja popravljam, ne moj claim)

Nullable `service`/`start_time`/`end_time` u modelu uvode 5 novih mypy
grešaka u `src/dentaland/services/booking.py` (linije 133, 143, 157, 202,
203) — taj fajl je pod DENT-006 claim-om (Crush aktivno radi tamo), pa ga
namjerno nisam dirao. Runtime ponašanje `booking.py` nije pogođeno (te
putanje koda uvijek rade sa `SCHEDULED` terminima koji imaju popunjene
vrijednosti), ali mypy to ne može statički dokazati poslije ove izmjene.
Treba popraviti kao dio DENT-006 review-a ili zaseban sitan follow-up —
najlakše dodavanjem `assert appt.service is not None` (i slično za
start/end) na mjestima gdje je `AppointmentService` upravo pročitao red
koji zna da je kompletan.

## Šta NIJE urađeno (namjerno, gated)

- Token generisanje za cancel/reschedule link.
- RBAC/login/autentifikacija na bilo kojem endpointu.
- Javni deployment, VPS, domena, `EXCLUDE` constraint/PostgreSQL migracija.

Sve navedeno ostaje blokirano dok se pravna pitanja iz `CLAUDE.md`
"Otvorena pitanja" ne riješe — nezavisno od toga da li backend radi
lokalno ili javno.

## Odbačene opcije

- Deljena overlap-check funkcija sa `booking.py` — odbačeno zbog aktivnog
  paralelnog rada na tom fajlu; duplirana mala funkcija je jeftinija od
  koordinacionog rizika.
- PostgreSQL lokalno (Docker) — odbačeno, `EXCLUDE` constraint je namjerno
  odvojen budući zadatak.
- Sentinel/placeholder vrijeme umjesto nullable `start_time` — odbačeno,
  nullable je iskreniji prikaz "još nije poznato".
- `Depends()` u default argumentima (FastAPI uobičajen obrazac) — ruff ga
  označava (B008); zamijenjeno `Annotated[...]` oblikom umjesto supresije.

## Review

**Nema nezavisan review — eksplicitan izuzetak, ne previd.** Standardni
HIGH proces (dva nezavisna reviewera prije human approval-a) je
preskočen na eksplicitan zahtjev Radovana (16.8.2026), koji je preuzeo i
review i human approval ulogu odjednom, na osnovu prikazane verifikacije
(62 testa, ruff, mypy u dirani fajlovima, i stvaran uvicorn smoke test sa
`httpx` van `TestClient`-a). Implementer (Claude) nije mogao sam sebe
reviewovati — ovaj zapis postoji da bude jasno da je korak svjesno
preskočen, ne zaboravljen, ako se kasnije nešto pokaže pogrešnim u ovom
kodu.

## Integration status

MERGED → INTEGRATION_VERIFIED → DONE. Mergovano u `main` bez independent review-a (vidi sekciju "Review" iznad — eksplicitan izuzetak). Post-merge integration gate: pun test suite (70/70), `ruff check` čist, `mypy` vraćen na poznat baseline (8 grešaka, sve u `desktop/`) poslije brze popravke `booking.py` regresije koja se pojavila kad su se DENT-006 i DENT-007 spojili (commit `65a61fd`, najavljeno kao follow-up u oba evidence fajla).
