---
task_id: DENT-IMPROVE-011
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit f9de00e, 2026-08-26), post-merge integration gate PASS (374 pytest, ruff, mypy, agent_sensors 0 findings, 6 Playwright E2E testova). Otvara DENT-IMPROVE-012 (PostgreSQL)."
review_summary: >-
  Codex runda 1: REJECT (F1 blocking, ne test-kvalitet - reuseExistingServer:
  !process.env.CI je tiho reuse-ovao nepoznat proces na portu 8000, dokazano
  sentinel-bazom da bi sintetski E2E podaci mogli zavrsiti u stvarnoj dev
  bazi). Implementer popravio na reuseExistingServer:false. Claude je
  nezavisno LICNO reprodukovao adversarni scenario PRIJE commit-a fixa
  (sentinel uvicorn na portu 8000, potvrdjen isti "already used" fail-fast).
  Codex runda 2: PASS (sam takodje ponovio scenario). Claude review:
  PASS_WITH_NOTES - administrativna napomena da se generic "Failed to fetch"
  poruka (OUT_OF_SCOPE_FINDING) zapise kao buduci mali DENT-IMPROVE
  kandidat. 409 scenario potvrdjen kao ne-postojeci u javnom flow-u (interni
  admin tok), ispravno nije izmisljen.
created_at: 2026-08-26
merged_at: 2026-08-26
---

# DENT-IMPROVE-011 — Browser E2E testovi javne forme (Playwright)

## Kontekst

`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, stavka 11 (Prioritet C1 nakon
DENT-IMPROVE-010, koji je već DONE). `web/tests/` trenutno sadrži samo
statične preview HTML fajlove (`desktop.html`, `flow.html`, `mobile.html`,
`privacy.html`) — nisu pravi browser end-to-end testovi, ne pokreću
stvaran backend niti provjeravaju stvarno ponašanje forme.

**Ovo je JEDINI trenutno neblokiran Prioritet C task** — DENT-IMPROVE-012
(PostgreSQL), 013 (Auth/RBAC), 014 (Audit), 015 (Production gate) svi
eksplicitno čekaju da ovaj task završi (`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`
sekcija 18, dependency graf).

## Trenutno stanje repoa (provjereno 26.8.2026, prije pisanja kontrakta)

- `web/` je čist statičan sajt (`index.html`, `app.js`, `style.css`,
  `privacy.html`) — **nema** `package.json`, `node_modules`, ni ikakav
  postojeći Node/npm setup. Ovo je PRVI put da se Node tooling uvodi u
  ovaj repo.
- Backend NE servira `web/` statički — komentar u `backend/main.py:89`
  eksplicitno kaže "web/ se otvara sa file:// ili drugog localhost".
  Implementer mora sam odlučiti kako servirati `web/` za testove (npr.
  Playwright-ov `webServer` config sa `python -m http.server` ili
  ekvivalent) — CORS je već otvoren (`allow_origins=["*"]`,
  `backend/main.py:93`) upravo zbog ovog cross-port scenarija.
- Relevantni javni endpointi (`backend/main.py`):
  - `POST /api/booking-requests` → `201` na uspjeh, rate-limited
    `@limiter.limit("10/minute")` (linija 126-127) — ovo je izvor 429
    scenarija.
  - `POST /api/booking-requests/{id}/confirm` → `409` na `OverlapError`
    (linija 173) — ovo je izvor 409 scenarija (ali provjeriti da li je
    ovaj endpoint uopšte dio JAVNE forme ili internog admin toka; ako je
    interni, 409 scenario iz backloga možda ne postoji u trenutnom javnom
    flow-u — implementer treba provjeriti i, ako scenario ne postoji,
    prijaviti kao `OUT_OF_SCOPE_FINDING`, ne izmišljati ga).

## Cilj

Mali broj visokovrijednih Playwright E2E scenarija protiv STVARNOG
lokalnog backend+web setupa (ne mock, ne statični preview).

**Preferovan alat: Playwright**, osim ako implementer nađe objektivan
razlog protiv (dokumentovati razlog ako se odstupi).

## Minimalni scenariji (iz backloga, tačno ovih 7 — ne više, ne manje bez razloga)

1. Validan submit → `201`.
2. Validacija obaveznog polja (npr. prazno ime/telefon/email → forma ne
   šalje zahtjev, prikazuje grešku).
3. Backend nedostupan → jasna poruka korisniku (ne tiha greška u konzoli).
4. `429` rate limit (11. zahtjev u minuti → forma prikazuje jasnu poruku,
   ne generičku grešku).
5. `409` konflikt **kada taj flow postoji** u javnoj formi (vidi napomenu
   gore — provjeriti prije pisanja, ne pretpostaviti).
6. Mobile viewport smoke test (forma je upotrebljiva na mobilnoj
   rezoluciji — barem da se glavni elementi vide i rade).
7. Privacy link postoji i vodi na `privacy.html` (ili ekvivalentnu
   stranicu).

## Constraint (iz backloga, eksplicitno)

**Ne pretvarati `web/` u React/Vite projekat samo radi testova.** `web/`
ostaje statičan HTML/JS/CSS sajt — Playwright i njegov `package.json`
idu u zaseban folder (npr. `web/tests/e2e/` ili `e2e/` u korijenu,
implementer bira, dokumentuje izbor u izvještaju) koji NE mijenja kako se
`web/` sam servira u produkciji.

## Tehnički zahtjevi

- Novi `package.json` (samo za Playwright, minimalne zavisnosti) + Node
  setup instrukcija u izvještaju (koja Node verzija je testirana).
- `.gitignore` dopuna: `node_modules/`, `test-results/`,
  `playwright-report/` (provjeriti da već ne postoje slični unosi prije
  dodavanja duplikata).
- Playwright `webServer` config koji pokreće I backend (uvicorn) I web
  static server automatski prije testova — cilj je "mogu se pokrenuti
  jednom komandom" (acceptance kriterijum iz backloga).
- Testovi koriste izolovanu/test bazu, ne postojeću dev/produkcijsku
  SQLite datoteku — provjeriti kako se backend trenutno konfiguriše za
  test okruženje (postoji li već `DENTALAND_DB_PATH` ili slična env
  varijabla) prije nego što se izmisli nov mehanizam.
- **Ne koristiti stvarne podatke pacijenata** (acceptance kriterijum iz
  backloga) — sintetski test podaci.

## Acceptance criteria (iz backloga)

- [ ] testovi rade protiv lokalnog backend+web setupa (stvaran HTTP,
      stvaran browser, ne mock);
- [ ] mogu se pokrenuti jednom komandom (dokumentovati tačnu komandu u
      izvještaju i, ako ima smisla, u `README.md`);
- [ ] ne koriste stvarne podatke pacijenata;
- [ ] svih 7 scenarija pokriveno (ili 6 + dokumentovan razlog zašto 409
      ne postoji u javnom flow-u, ako je to slučaj);
- [ ] `web/` sam po sebi nije pretvoren u build-tooling projekat;
- [ ] postojeći `pytest tests/ -q`, `ruff check`, `mypy` ostaju čisti
      (ovaj task ne dira Python kod osim ako je apsolutno nužno za test
      fixture/config, što treba biti minimalno i dokumentovano).

## Allowed paths

```text
web/tests/e2e/**              (novo, ili implementerov izabran ekvivalentan put)
package.json                  (novo, ili unutar e2e foldera — implementer bira)
.gitignore
README.md                     (samo ako se dodaje E2E run instrukcija)
agent_reports/**
```

## Forbidden paths

```text
desktop/**
src/dentaland/**
backend/main.py                (READ-ONLY referenca; ako treba izmjena za testabilnost, prijaviti OUT_OF_SCOPE_FINDING prije nego što se dira)
web/index.html
web/app.js
web/style.css
web/privacy.html
models.py
migrations/**
```

(`backend/main.py` je namjerno u forbidden — ako implementer otkrije da
je testu STVARNO potreban mali hook u backend kodu (npr. test-only DB
reset endpoint), to je legitiman `OUT_OF_SCOPE_FINDING`/scope pitanje,
ne nešto što se tiho doda.)

## Review

Standardan REF/DENT-IMPROVE proces: Codex pa Claude, human approval
prije merge-a. Codex treba posebno provjeriti da testovi STVARNO
pokreću browser protiv živog servera (ne mockovan `fetch`), i da "jednom
komandom" tvrdnja stvarno radi na čistom checkout-u.

## Koordinacija

Nema zavisnosti unutar REF/DENT-IMPROVE backloga — jedini trenutno
neblokiran Prioritet C task. **Ne dijeliti ovaj task na dva paralelna
implementera** — jedan dijeljen Playwright harness/scaffolding (config,
webServer, fixtures) ne dozvoljava čist zero-overlap paralelizam, i
acceptance eksplicitno traži jedinstven "jednom komandom" setup.
