# DENT-IMPROVE-011 — Codex independent review (test kvalitet)

```yaml
verdict: REJECT
scope: PASS
acceptance: FAIL
architecture: PASS
security: PASS_WITH_NOTES
blocking_findings:
  - F1: Lokalni Playwright config moze reuse-ovati postojeci backend na portu 8000 i tada zaobilazi izolovani DENTALAND_DB_PATH, pa E2E zahtjevi mogu pisati u dev bazu.
```

## CILJ

Provjeriti da novi Playwright suite koristi stvarni browser i stvarne HTTP
servere, pokriva ugovorene javne tokove i garantuje izolovanu test bazu.

## URAĐENO

- Potvrđeni lokalni i remote commit `aac3611` na grani
  `task/DENT-IMPROVE-011-playwright-e2e`.
- Scope je čist: `.gitignore`, `README.md`, implementer izvještaj i novi
  `web/tests/e2e/**`. `backend/main.py`, `web/index.html`, `web/app.js`,
  `web/style.css` i `web/privacy.html` nisu dirani.
- `.gitignore` minimalno dodaje `node_modules/`, `test-results/` i
  `playwright-report/`; README sadrži tačnu setup/run sekciju.
- `web/` nije pretvoren u build projekat; Node tooling je izolovan u
  `web/tests/e2e/`.

### Stvarni browser i živi serveri

Samostalni `npx playwright test` iz `web/tests/e2e/` dao je:

```text
6 passed (10.9s)
```

Output pokazuje pokretanje novog uvicorn procesa, `python -m http.server`,
stvarne GET zahtjeve za HTML/JS/CSS/assets/privacy stranicu i Chromium test
worker. Validan submit čeka stvarni POST response i potvrđuje HTTP **201**;
nema `page.route`, fetch mocka ili API stub-a. Run je kreirao novu
`dentaland-e2e-<pid>.db` bazu od 24576 B u OS temp direktoriju i ugasio oba
servera po završetku.

`playwright.config.js` zaista ima dva `webServer` unosa:

- uvicorn `127.0.0.1:8000`, repo root, `PYTHONPATH=src`, temp
  `DENTALAND_DB_PATH`;
- static server `127.0.0.1:8080`, cwd `web/`.

Postojeći backend CORS `allow_origins=["*"]` dozvoljava cross-port poziv, što
je potvrđeno uspješnim browser submitom.

### F1 — izolacija baze nije garantovana (blocking)

Oba servera imaju:

```javascript
reuseExistingServer: !process.env.CI
```

To znači da standardna lokalna komanda iz README-a (`npm test` / `npx
playwright test`) neće pokrenuti izolovani backend ako je port 8000 već
zauzet odgovarajućim HTTP serverom. U tom slučaju `env.DENTALAND_DB_PATH` iz
Playwright configa nikad se ne primijeni.

Adversarni repro je izveden bez stvarnih podataka:

1. pokrenut je uvicorn na 8000 sa jedinstvenom sentinel temp bazom;
2. iz E2E foldera pokrenut je samo test validnog submita;
3. Playwright nije ispisao pokretanje svog uvicorn procesa, nego je
   reuse-ovao postojeći;
4. test je prošao (`1 passed`) i sentinel baza je kreirana/popunjena na
   24576 B (`SENTINEL_DB_WRITTEN`).

Sa stvarnim već otvorenim dev backendom isti mehanizam bi upisao sintetske
booking zahtjeve u dev bazu; puni suite bi dodatno poslao rate-limit burst.
To direktno krši acceptance zahtjev „testovi koriste izolovanu/test bazu, ne
postojeću dev/produkcijsku SQLite datoteku“.

Minimalna popravka: backend `webServer` mora imati
`reuseExistingServer: false` (poželjno oba servera radi determinističnosti),
ili ekvivalentan fail-fast mehanizam koji nikad ne koristi nepoznat proces na
8000. Nakon popravke ponoviti čisti run i adversarni scenario sa zauzetim
portom: očekivanje je da Playwright prekine zbog zauzetog porta, a ne da test
prođe kroz postojeći backend.

### OUT_OF_SCOPE nalazi

**409:** implementerovo tumačenje je tačno. `web/app.js` ima samo jedan fetch,
`POST /api/booking-requests`. Endpoint
`POST /api/booking-requests/{id}/confirm`, jedino mjesto koje mapira
`OverlapError` na 409, prima admin podatke (`doctor_id`, `service_id`,
`start_time`) i javna forma ga ne poziva. Ne treba izmišljati 409 browser flow
koji ne postoji.

**Backend nedostupan:** test stvarno preusmjerava `DENTALAND_API_BASE` na
nedostupan port prije učitavanja `app.js`, zatim potvrđuje da je
`.submit-error` vidljiv i neprazan. Stvarni `catch` prikazuje
`error.message`, pa Chromium daje generički `Failed to fetch`. Greška nije
tiha; lokalizacija/ljepši tekst zahtijeva forbidden `web/app.js` izmjenu i
korektno je prijavljena van scope-a.

### Standardna verifikacija

- `pytest tests/ -q`: **374 passed**, 11 warnings.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`:
  **All checks passed**.
- `mypy src/dentaland desktop backend`: **Success**, 52 source fajla.
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.

## NE DIRATI

- Ne mijenjati produkcijski backend ili javni web kod radi F1; problem je u
  Playwright harness konfiguraciji.
- Ne dodavati lažni 409 browser scenario javnoj formi.
- Ne lokalizovati network-error poruku unutar ovog taska bez odobrenog
  proširenja scope-a.

## SLJEDEĆE

DENT-IMPROVE-011 ostaje **REJECT** dok lokalni E2E harness ne garantuje
izolovanu bazu i odbije reuse nepoznatog servera. Nakon minimalnog config
fixa potreban je kratki Codex re-review sa čistim i zauzeti-port reproom;
zatim Reviewer 2 i Radovan human approval.
