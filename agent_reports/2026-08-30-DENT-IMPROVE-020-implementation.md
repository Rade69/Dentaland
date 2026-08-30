---
task_id: DENT-IMPROVE-020
risk: MEDIUM
implementer: claude
reviewers: [codex]
status: "Implementacija gotova, uzivo testirano protiv test VPS-a, ceka Codex review"
created_at: 2026-08-30
---

# DENT-IMPROVE-020 — Desktop daljinski demo (Novi zahtjevi) — evidence

Vidi `agent_reports/DENT-IMPROVE-020-task-contract.md` za pun kontekst i
dogovoren obim.

## Šta je implementirano

1. **`backend/main.py`** — `GET /api/doctors` (samo aktivni),
   `GET /api/services` (sa trajanjem/bufferom) — RECEPTION-zaštićeni,
   rate limited (30/minute), ponovo koriste postojeće servisne funkcije
   (`settings.doctors`, `appointments.service_options`), nula nove
   poslovne logike u ruteru.
2. **`desktop/api_client/`** (nov paket) — `DentalandApiClient`:
   `login`, `get_pending_requests`, `get_doctors`, `get_service_choices`,
   `confirm_pending`, `reject_pending`. Mrežne greške → `ConnectionFailedError`,
   401 → `AuthenticationFailedError`, 409 na confirm → `OverlapError`
   (isti tip koji `RequestController` već hvata), 404 → `ValueError`.
3. **`desktop/remote_store.py`** — `RemoteRequestsStore`, uzak adapter
   (duck-typing na `AppointmentService` obrazac) koji implementira
   TAČNO ono što `DashboardPanels`/`RequestController` pozivaju.
4. **`desktop/remote_demo.py`** — potpuno odvojen entry point: login
   `QDialog` (RBAC) → `QMainWindow` sa SAMO `DashboardPanels`.
   `desktop/app.py`/`desktop/views/main_window.py` NISU dirani — potvrđeno
   `git diff --stat` (prazan izlaz, exit 0).

## Verifikacija — automatska

- `pytest tests/ -q` bez `DATABASE_URL_TEST`: **446 passed, 20 skipped**.
- `pytest tests/ -q` sa `DATABASE_URL`+`DATABASE_URL_TEST` (real Postgres):
  **466 passed, 0 failed**.
- `ruff check .` — samo 5 pre-postojećih grešaka u `scripts/coordination.py`
  (nepovezano), svi fajlovi ovog taska čisti.
- `mypy src backend desktop` — **Success: no issues found in 59 source
  files**.
- `python scripts/agent_sensors.py --all` — **0 blocking findings**.
- `git diff --stat desktop/app.py desktop/views/main_window.py` —
  **prazan izlaz** (nula izmjena, kako je i traženo).

## Verifikacija — STVARNO uživo protiv test VPS-a (30.8.2026)

Grana privremeno checkout-ovana na test VPS-u (isti obrazac kao
DENT-IMPROVE-018/019), backend restartovan, kreiran sintetički RECEPTION
nalog (`demo-sestra`, preko `scripts/create_user.py`) za potrebe testa.

**Headless Qt smoke-test** (`QT_QPA_PLATFORM=offscreen`, stvarna mreža,
NE mock) — konstruisan pravi `RemoteDemoWindow` sa pravim
`DentalandApiClient` prijavljenim na `https://169-58-208-91.nip.io`:

```
LOGIN OK
Pending box title: Novi zahtjevi (1)
Doctors from API: ['TEST Doktor']
Services from API: [(1, 'TEST Usluga')]
```

Dashboard panel je STVARNO prikazao real-time stanje sa VPS baze
(postojeći sintetički zahtjev `id=1` "Test VPS Deployment", ostavljen
kao dokaz iz ranijeg deployment testa).

**Potvrda kroz isti `store` objekat koji GUI koristi** (ne zaobilazna
skripta — `RemoteRequestsStore.confirm_pending`, identičan poziv kao
kad `RequestController.process_pending_request` pozove store nakon
klika na "Potvrdi" u `ProcessRequestDialog`):

```
Pending prije: [(1, 'Test VPS Deployment')]
confirm_pending pozvan bez greske
Pending poslije: []
```

Nezavisno provjereno direktno u bazi:
```
status=SCHEDULED doctor_id=1 service_id=1
start_time=2026-08-31 12:00:00+00:00 confirmed_at=2026-08-30 12:53:14+00:00
```

**Šta OVO dokazuje**: `desktop/api_client` → HTTPS → RBAC prijava →
`GET /api/doctors`/`GET /api/services`/`GET /api/booking-requests` →
`POST /api/booking-requests/{id}/confirm` → `confirm_request` servisni
poziv → stvarna promjena u bazi — CIJELI novi lanac koda iz ovog taska
je stvaran, ne samo jedinično testiran sa mock-ovima.

**Šta OVO NE dokazuje (priznanje ograničenja)**: nisam vizuelno vidio
Qt prozor niti fizički kliknuo dugme "Potvrdi" unutar
`ProcessRequestDialog` — headless test je pozvao `store.confirm_pending`
direktno (isti poziv koji taj klik pravi), ne kroz stvaran klik miša na
dugme i popunjavanje dijaloga. `ProcessRequestDialog` sam je
nepromijenjen, već korišten i testiran kod (dijeli se sa lokalnom
aplikacijom), pa je rizik da SAM dijalog ne radi nizak, ali NIJE lično
potvrđen ovim testom. Ako Radovan želi potpunu vizuelnu potvrdu
(stvaran klik mišem), treba pokrenuti `remote_demo.py` lično — vidi
"Kako pokrenuti" ispod.

**Email/Telegram za ovaj konkretan confirm poziv NISU provjereni** —
SMTP/Telegram env varijable nisu bile postavljene na VPS-u tokom ovog
kruga (namjerno, da se izbjegne dupliranje već potvrđenog
DENT-IMPROVE-018 dokaza). Mehanizam je identičan (`confirm_request`
poziva `send_appointment_confirmed` bez obzira ko je pozivalac — vidi
`src/dentaland/services/requests.py` komentar "radi bez obzira ko poziva
confirm_request") — već dokazano u DENT-IMPROVE-018 evidence-u da radi
kad su env varijable postavljene.

Nakon testa: VPS vraćen na `main` (`git checkout main`, backend
restartovan, sanity-check `GET /` → 200). `demo-sestra` RECEPTION nalog
NAMJERNO ostavljen na test bazi (sintetički, bezopasan) za budući ručni
demo klik ako Radovan želi vizuelno potvrditi.

## Kako pokrenuti (za Radovanovu ličnu vizuelnu potvrdu)

```
set DENTALAND_REMOTE_API_BASE=https://169-58-208-91.nip.io
python desktop/remote_demo.py
```

Prijava: `demo-sestra` / (lozinka poslana Radovanu direktno u chatu, ne
ovdje — isti princip kao ostali kredencijali u ovom projektu) —
sintetički test nalog, ostavljen na VPS test bazi upravo za ovu svrhu.
Napomena: pošto je
appointment `id=1` upravo potvrđen ovim testom, lista "Novi zahtjevi"
će biti prazna dok se ne pošalje nov zahtjev sa javne forme
(`https://169-58-208-91.nip.io/`) za novi klik-test.

## Sljedeći koraci

1. Codex review.
2. Human approval.
3. Radovanova lična vizuelna potvrda (opciono, ako želi stvaran klik
   test prije odobrenja).
