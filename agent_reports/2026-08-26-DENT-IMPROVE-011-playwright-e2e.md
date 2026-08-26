---
task_id: DENT-IMPROVE-011
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: "IMPLEMENTED — čeka review. Bez commit-a (eksplicitna instrukcija: čekati zahtjev)."
verification: "Playwright 6 passed (stvarni browser + backend), pytest 374 passed, ruff clean, mypy no issues in 52 files."
created_at: 2026-08-26
---

# DENT-IMPROVE-011 — Implementer izvještaj (Pi)

## Šta je urađeno

Playwright E2E suite koji pokreće STVARAN FastAPI backend (uvicorn) i
STVARAN statičan web server, i testira javnu formu u pravom browseru — ne
mock, ne statični preview. `web/` NIJE pretvoren u build-tooling projekat.

## Dizajn-odluke (kontrakt ih prepušta implementeru)

- **Gdje ide Node tooling:** `web/tests/e2e/` — zaseban folder uz postojeće
  statične preview fajlove u `web/tests/`. `web/` sam ostaje netaknut.
- **Kako se servira `web/`:** Playwright `webServer` #2 = `python -m
  http.server 8080 --bind 127.0.0.1` (cwd = `web/`). Backend je `webServer`
  #1 = `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
  (cwd = repo root, `PYTHONPATH=src`). CORS je već otvoren (`allow_origins=["*"]`)
  — cross-port 8080 → 8000 radi bez izmjena.
- **Node verzija:** testirano na Node `v24.12.0`, npm `11.7.0`, Playwright
  `1.62.1` (Chromium).
- **Test baza:** `DENTALAND_DB_PATH` (postojeća env varijabla, `backend/main.py`
  je već čita) → temp fajl `dentaland-e2e-<pid>.db`. Ne dira dev/produkcijsku
  bazu.
- **Email no-op:** SMTP env varijable se NAMJERNO ne postavljaju —
  `send_booking_confirmation` preskače kad `DENTALAND_SMTP_HOST` nedostaje
  (potvrđeno čitanjem `notifications.py`). Nema stvarnih email-ova.
- **`workers: 1`:** rate limiter je 10/minute po IP-u (127.0.0.1), pa
  sekvencijalno izvršavanje drži 429 scenario determinističkim.

## Fajlovi

```text
web/tests/e2e/package.json          (novo — @playwright/test)
web/tests/e2e/package-lock.json     (novo — npm install)
web/tests/e2e/playwright.config.js  (novo — 2× webServer)
web/tests/e2e/tests/booking.spec.js (novo — 6 scenarija)
.gitignore                          (dodato: node_modules/, test-results/, playwright-report/)
README.md                           (dodata E2E run sekcija)
agent_reports/**                    (ovaj izvještaj)
```

## Scenariji (7 iz backloga → 6 implementirano + 1 OUT_OF_SCOPE)

1. Validan submit → `201` + UI potvrda ("ZAHTJEV PRIMLJEN!") — assert statusa
   kroz `page.waitForResponse`.
2. Prazno obavezno polje (ime) onemogućava `#continue-button`.
3. Backend nedostupan (forma usmjerena na 127.0.0.1:9999 preko
   `window.DENTALAND_API_BASE`) → `.submit-error` vidljiv i ne-prazan.
4. 429 rate limit — 12 sintetskih POST-ova direktno na API iscrpe limiter,
   UI submit → poruka "Previše zahtjeva".
5. ~~409 konflikt~~ → **OUT_OF_SCOPE_FINDING** (vidi niže).
6. Mobile viewport (375×667) — naslov, kalendar, korak 2 i forma vidljivi.
7. Privacy link → otvara `privacy.html` u novom tabu.

## OUT_OF_SCOPE_FINDING-ovi

### F1 — 409 scenario ne postoji u javnom flow-u

`POST /api/booking-requests/{id}/confirm` (izvor `409` na `OverlapError`)
je INTERNI admin tok (prima `doctor_id`/`service_id`/`start_time`) — javna
forma (`web/app.js`) ga NIKAD ne poziva; ona samo šalje
`POST /api/booking-requests`. Zato 409 scenario ne postoji u javnom flow-u i
nije izmišljen test.

```yaml
finding: OUT_OF_SCOPE_FINDING
description: 409 scenario iz backloga ne postoji u javnoj formi (confirm endpoint je interni admin tok)
location: backend/main.py:139 (confirm), web/app.js (ne poziva confirm)
risk: LOW
proposed_task: none — pokriti 409 kroz admin/desktop tok ako zatreba zaseban E2E
```

### F2 — backend-nedostupan poruka je generična "Failed to fetch"

Scenario 3 je pokriven (test potvrđuje da se poruka PRIKAZUJE u
`role="alert"` elementu, ne tiha konzolna greška), ali stvarni tekst je
`"Failed to fetch"` (engleski, generičan) jer `web/app.js` ne hvata network
grešku posebno. Poboljšanje poruke (npr. "Servis trenutno nije dostupan…")
bi zahtijevalo izmjenu `web/app.js` — forbidden path za ovaj task.

```yaml
finding: OUT_OF_SCOPE_FINDING
description: backend-nedostupan poruka je "Failed to fetch" (engleski generičan); prijateljskija poruka zahtijeva izmjenu web/app.js
location: web/app.js (submitBookingRequest / catch)
risk: LOW
proposed_task: DENT-IMPROVE-0XX — lokalizovati/razjasniti network-error poruku u web/app.js
```

## Verifikacija (doslovni rezultati)

```text
$ cd web/tests/e2e && npx playwright test
6 passed (12.6s)   # stvarni uvicorn backend + http.server + Chromium

$ python -m pytest tests/ -q
374 passed, 11 warnings

$ python -m ruff check src/dentaland desktop backend tests scripts/agent_sensors.py
All checks passed!

$ python -m mypy src/dentaland desktop backend
Success: no issues found in 52 source files
```

## Tačna komanda za pokretanje

```bash
cd web/tests/e2e
npm install                        # jednokratno
npx playwright install chromium    # jednokratno
npx playwright test                # ili: npm test  ← svaki put
```

`npm test` sam podiže backend + web server (Playwright `webServer` config),
pokreće 6 scenarija, i gasi servere na kraju.

## Nije urađeno / namjerno izostavljeno

- Nema commit-a — čekam zahtjev.
- `backend/main.py`, `web/index.html`, `web/app.js`, `web/style.css`,
  `web/privacy.html` nisu dirani (forbidden paths).
- Python kod nije diran (potvrđeno: `git status` pokazuje samo `.gitignore`,
  `README.md`, `web/tests/e2e/**`, `agent_reports/**`).
