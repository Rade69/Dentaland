---
task_id: DENT-IMPROVE-013
risk: HIGH
implementer: claude
reviewers: [codex, pi]
status: "Codex PASS_WITH_NOTES (Fix runda 1 potvrđena). Pi N1 popravljen. Čeka Crush (opciono) i human approval."
created_at: 2026-08-27
---

## Post-review addendum (27.8.2026) — Pi N1 riješen

**N1 (Pi, kozmetički, non-blocking)** — `hash_password` nije imao trajan
test da stvarno proizvodi Argon2id hash (samo ručno potvrđeno u
izvještaju). Dodat `tests/test_auth.py::test_hash_password_koristi_argon2id`
— assert na `$argon2id$` PHC string prefiks. `pytest tests/ -q` → **396
passed, 2 skipped** (bilo 395), `ruff` čist.

**Napomena o Pi-jevom pitanju vezanom za DENT-IMPROVE-012** (nije nalaz za
OVAJ task, samo razjašnjenje): Pi je u istom review-u pitao da li se treba
vratiti na raniji DENT-012 nalaz (4 failed testa zbog `migrations/env.py`
`DATABASE_URL` interakcije). Potvrđeno da JE već riješeno i mergovano —
guard fix (`_ALEMBIC_INI_DEFAULT_URL` provjera) je prisutan na trenutnom
`main` (merge `824590f`), i ista 4 testa su ponovo pokrenuta sa
`DATABASE_URL`+`DATABASE_URL_TEST` istovremeno postavljene na trenutnom
`main` → **4 passed**. Vidi `agent_reports/2026-08-27-DENT-IMPROVE-012-postgres-migration.md`
sekciju "Fix runda 2" za pun kontekst — nije zapušten nalaz.

---

## Fix runda 1 (Codex review, `2026-08-27-DENT-IMPROVE-013-review-codex.md`, verdict REJECT)

**F1 (HIGH, blocking) — popravljeno.** `change_password` je koristio DVIJE
odvojene transakcije/commit-e: prvo commit izmjene `password_hash`, pa tek
onda (u posebnoj, novoj sesiji) commit opoziva svih aktivnih sesija
korisnika. Codex je adversarnom probom pokazao da bi kvar u drugom koraku
(bilo kakav izuzetak nakon prvog commita) ostavio novu lozinku upisanu dok
bi stare sesije ostale validne — direktno rušeći sigurnosni invarijant
zbog kojeg je invalidacija uopšte tražena (kompromitovana lozinka +
ukradeni token = napadač zadržava pristup i poslije "promjene" lozinke).

Nezavisno reprodukovano LIČNO prije fixa (privremeno vraćen stari
dvotransakcijski kod, potvrđen identičan kvar: stara lozinka prestane
raditi ČAK I kad drugi korak eksplicitno pukne — dokaz da nije bio teorijski
rizik). Fix: `_revoke_active_sessions` izdvojen kao helper koji radi NA
POSTOJEĆOJ sesiji bez sopstvenog commit-a; `change_password` sad radi hash
izmjenu i opoziv sesija u JEDNOJ `with session_factory() as session:` sa
JEDNIM `session.commit()` na kraju — bilo koji izuzetak prije tog commit-a
rollback-uje CIJELU transakciju, ne samo pola. `invalidate_all_sessions_for_user`
(javni API, i dalje koristi izvana) sad interno poziva isti `_revoke_active_sessions`
helper.

Dodat adversarni regresioni test
`tests/test_auth.py::test_promjena_lozinke_je_atomska_sa_opozivom_sesija` —
monkeypatch-uje `_revoke_active_sessions` da baci `RuntimeError` (simulira
Codexov tačan scenario), pa potvrđuje da NAKON izuzetka: (1) stara sesija je
i dalje validna, (2) stara lozinka i dalje radi, (3) nova lozinka NE radi.
Potvrđeno da test PADA sa starim (dvotransakcijskim) kodom i PROLAZI sa
fixom — prava regresiona zaštita, ne kozmetički test.

Verifikacija nakon fixa: `pytest tests/ -q` → **395 passed, 2 skipped**
(bilo 394 prije novog testa). `ruff`/`mypy` (53 fajla)/`agent_sensors.py
--all` → svi čisti.

---

# DENT-IMPROVE-013 — Autentifikacija + RBAC — finalni izvještaj

## Šta je urađeno

1. **`src/dentaland/models.py`** — dodati `UserRole` (StrEnum: RECEPTION/
   DENTIST/ADMIN), `User` (username unique, `password_hash`, `role`,
   `is_active`, `created_at`), `Session` (`user_id` FK, `token_hash`
   unique, `expires_at`, `created_at`, `revoked_at`). Ništa postojeće
   dirano.
2. **`src/dentaland/services/auth.py`** (novo) — `hash_password`/
   `verify_password` (Argon2id preko `argon2-cffi`), `authenticate_user`
   (generička greška + dummy-hash verifikacija na nepostojeći username,
   timing-zaštita), `create_session`/`validate_session`/
   `invalidate_session`/`invalidate_all_sessions_for_user`,
   `change_password` (invalidira sve sesije korisnika). Token: sirov
   `secrets.token_urlsafe(32)` nikad upisan, SHA-256 hash u bazi,
   `hmac.compare_digest()` za poređenje.
3. **`backend/main.py`** — `POST /api/auth/login` (`@limiter.limit("5/minute")`,
   odvojeno od `/api/booking-requests` 10/minute), `POST /api/auth/logout`,
   `CurrentUserDep`/`require_role([...])` (isti `Annotated[Type, Depends(...)]`
   obrazac kao `SessionFactoryDep`). `require_role(["RECEPTION"])`
   primijenjen na `GET /api/booking-requests`, `.../confirm`, `.../reject`.
   Login pokušaji idu u `logging` (`dentaland.auth` logger) — username,
   ishod, NIKAD lozinka.
4. **Alembic migracija** `e5f6a7b8c9d0_users_sessions.py`
   (`down_revision = d4e5f6a7b8c9`, potvrđeno kao head prije pisanja) —
   kreira `users`/`sessions`. Upgrade i downgrade ručno provjereni na
   privremenoj SQLite bazi (vidi "Verifikacija" ispod).
5. **`scripts/create_user.py`** (novo) — interaktivan CLI, `getpass` za
   lozinku (dva puta, potvrda), min. 8 znakova, provjera duplikata
   username-a prije prompta za lozinku. Testirano end-to-end (monkeypatch
   `getpass` u ovom okruženju jer je pravi Windows `getpass` vezan
   direktno za konzolu, ne za stdin pipe — vidi "Verifikacija").
6. **`pyproject.toml`** — dodat `argon2-cffi>=23.1`.
7. **`tests/test_auth.py`** (novo, 20 testova) — login uspjeh/neuspjeh
   (generička greška, identičan JSON za pogrešnu lozinku i nepostojeći
   username), neaktivan nalog, 401 na sva tri staff endpointa bez
   autentifikacije, 403 za `DENTIST` i eksplicitno za `ADMIN` (sva tri
   endpointa), `RECEPTION` uspješno prolazi kroz sve tri, logout
   invalidira sesiju, rate limit na login (odvojen od booking-request —
   testirano da booking-request i dalje radi kad je login kvota
   potrošena), promjena lozinke invalidira sve sesije, spot-check da
   lozinka/token nisu u response body-ju ni u uhvaćenom `caplog` izlazu.

## Nužne posljedične izmjene (ne proširenje obima)

Zaštita tri postojeća endpointa nužno mijenja njihovo ponašanje za
postojeće pozivaoce bez autentifikacije — bez ažuriranja postojećih
testova, acceptance kriterijum "postojeći pytest ostaje čist" bi bio
nemoguć:

- **`tests/test_backend.py`** — dodat `reception_session` fixture (kreira
  `RECEPTION` korisnika, loguje se, cookie ostaje vezan za `client`);
  primijenjen na 6 postojećih testova koji pozivaju
  `GET /booking-requests`/`confirm`/`reject`. `client` fixture sada radi
  preko `base_url="https://testserver"` (potrebno za `Secure` cookie —
  vidi tehničku odluku ispod) i poziva `limiter.reset()` (bez njega,
  `Limiter` je modul-nivo singleton dijeljen kroz cijelu pytest sesiju —
  kvota bi curila između testova/fajlova).
- **`tests/test_models.py`** — `test_sve_tabele_su_kreirane` proširen sa
  `users`/`sessions` (test eksplicitno nabraja SVE očekivane tabele).

Nijedna poslovna logika u tim fajlovima nije mijenjana, samo
autentifikacijski predislov dodat gdje ga nova zaštita zahtijeva.

## Tehnička odluka: cookie-based sesija (ne bearer token)

`HttpOnly` + `Secure` + `SameSite=Strict` cookie. Razlog: nema JS
klijenta u ovom obimu koji bi morao ručno rukovati tokenom — cookie se
šalje automatski na svaki naredni zahtjev, `HttpOnly` sprečava
XSS-eksfiltraciju (bearer token bi vjerovatno završio u `localStorage`,
dostupan JS-u). Vidi "Odbačene opcije" u planu za punu argumentaciju.

**CSRF**: `SameSite=Strict` bez punog CSRF token mehanizma je dovoljno ZA
SADA. Provjereno grep-om (ne preuzeto na riječ iz kontrakta):

```
grep -rn "httpx|import requests|QNetworkAccessManager|urlopen|http\.client" desktop/   → No matches found
grep -rn "fetch\(|api/" web/                                                          → SAMO web/app.js:211
                                                                                          poziva POST /api/booking-requests (javni)
```

Nema browser-based staff klijenta koji bi mogao slati cross-origin
zahtjeve na tri zaštićena endpointa — tvrdnja iz kontrakta je stvarno
tačna. Ako se doda admin web panel u budućnosti, CSRF token mehanizam
mora biti dodat tada.

**Test posljedica**: `Secure` cookie se ne šalje nazad httpx cookie jar-u
na plain `http://` — `TestClient(app, base_url="https://testserver")`
korišten u `tests/test_auth.py` i `tests/test_backend.py` (ASGI transport
ne pravi stvarnu TLS konekciju, samo mijenja scheme string koji cookie
jar provjerava).

## Acceptance kriterijumi

- [x] neautentifikovan poziv na sva tri staff endpointa → 401
      (`test_neautentifikovan_get_pending_vraca_401`,
      `..._confirm_vraca_401`, `..._reject_vraca_401`)
- [x] autentifikovan pogrešne uloge → 403, testirano za `DENTIST` I
      `ADMIN` (ne samo nepostojeći korisnik) —
      `test_dentist_ne_prolazi_na_confirm_vraca_403`,
      `test_admin_ne_prolazi_na_{confirm,reject,get_pending}_vraca_403`
- [x] `RECEPTION` uspješno prolazi kroz sva tri endpointa
- [x] lozinke Argon2id hash (`$argon2id$...` prefiks provjeren ručno),
      nikad plaintext
- [x] login generička greška — identičan JSON za pogrešnu lozinku i
      nepostojeći username (`test_login_pogresna_lozinka_i_nepostojeci_username_vracaju_identicnu_gresku`)
- [x] login sopstveni rate limit (5/minute), odvojen od booking-request
      (10/minute) — potvrđeno testom koji troši login kvotu pa provjerava
      da booking-request I DALJE radi
- [x] sesija ima `expires_at`, invalidira se na logout
- [x] promjena lozinke invalidira sve postojeće sesije
      (`test_promjena_lozinke_invalidira_sve_postojece_sesije`)
- [x] lozinka/token se ne pojavljuju u response/logu — provjereno testom
      (`test_login_response_ne_sadrzi_lozinku_ni_token`,
      `test_login_pokusaji_se_loguju_bez_lozinke`), plus ručni grep kroz
      diff (vidi ispod)
- [x] `scripts/create_user.py` radi, ne prima lozinku kao CLI argument —
      testirano end-to-end (monkeypatch `getpass`, jer pravi
      Windows-console `getpass` ne čita iz pipe-ovanog stdin-a — to je
      ograničenje test okruženja, ne skripte)
- [x] `pytest tests/ -q` → **394 passed, 2 skipped** (baseline prije bio
      374 passed, 2 skipped — +20 novi `test_auth.py`)
- [x] `ruff check src/dentaland desktop backend tests` (CI scope,
      `.github/workflows/ci.yml:56`) → čisto
- [x] `mypy src/dentaland desktop backend` (CI scope, `ci.yml:59`) → 53
      fajlova, 0 grešaka
- [x] `python scripts/agent_sensors.py --all` → 0 blocking findings
- [x] `desktop/**`, `web/**` netaknuti (`git status --short` potvrđuje)
- [x] nema nove DB audit tabele — samo `logging.getLogger("dentaland.auth")`

Svi acceptance kriterijumi ispunjeni.

## OUT_OF_SCOPE_FINDING — RIJEŠENO (27.8.2026, van ovog taska)

Radovan je potvrdio i tražio popravku oba gap-a odmah. Popravljeno
direktno na `main` (`0c038d8`, commitovano i push-ovano — mehanička CI
izmjena, bez arhitektonske odluke, nije zahtijevala poseban Task
Contract) i kopirano u ovaj worktree (`.github/workflows/ci.yml`, van
`allowed_paths`, ali identično main-ovoj već-odobrenoj verziji — trivijalno
za merge, ništa novo za reviewera da procjenjuje). Originalni nalaz
ispod ostaje kao istorijski zapis šta je otkriveno i zašto.

**`.github/workflows/ci.yml` (linije 37-50) ne instalira `argon2-cffi`**
(niti `psycopg2-binary` iz DENT-IMPROVE-012 — postojeći, ranije
neprijavljen gap, potvrđeno da ni DENT-012 plan ni izvještaj to nisu
ažurirali). CI instalira eksplicitnu listu paketa, ne
`pip install -e .[dev]` iz `pyproject.toml`, pa novododata zavisnost
NEĆE automatski stići u CI okruženje. **Efekat**: CI će pući na
`ModuleNotFoundError: No module named 'argon2'` čim pokuša
`pytest tests/ -q` (koji uvozi `tests/test_auth.py` →
`dentaland.services.auth` → `argon2`).

Nije popravljeno u ovom zadatku — `.github/workflows/ci.yml` nije u
`allowed_paths` kontrakta, a CI konfiguracija je zajednička infrastruktura
van "auth/RBAC" opsega. Preporuka: dodati `"argon2-cffi>=23.1"` (i,
odvojeno, `"psycopg2-binary>=2.9"` za DENT-012 gap) u instalacionu listu
prije merge-a ove grane, ili prebaciti CI na
`pip install -e .[dev]` da se ovakav gap strukturno ne ponavlja.

## Verifikacija — komande i rezultati

```
pytest tests/ -q
  → 394 passed, 2 skipped, 12 warnings

ruff check src/dentaland desktop backend tests   (CI scope)
  → All checks passed!

mypy src/dentaland desktop backend               (CI scope)
  → Success: no issues found in 53 source files

python scripts/agent_sensors.py --all
  → Result: 0 blocking findings

alembic upgrade head   (privremena SQLite baza)
  → a1b2c3d4e5f6 → b2c3d4e5f6a7 → c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0
  → tabele: users, sessions kreirane; sve postojeće tabele netaknute

alembic downgrade -1
  → users, sessions čisto uklonjene, ostale tabele netaknute

scripts/create_user.py end-to-end (getpass monkeypatched)
  → kreiranje uspješno (Argon2id hash, verify_password vraća True)
  → duplikat username-a → exit 1, bez prompta za lozinku
  → prekratka lozinka → retry poruka, ne pada
  → lozinke se ne poklapaju → retry poruka, ne pada
```

Diff spot-check (`grep -rn "log\.|logger\.|print(" ... | grep -i
"password|token|lozink"`) → jedini pogodak je poruka
"Lozinke se ne poklapaju" (tekst, ne vrijednost).

## Odbačene opcije

Vidi `agent_reports/2026-08-27-DENT-IMPROVE-013-plan.md` ("Odbačene
opcije") — `Authorization: Bearer` header (odbačen), ADMIN automatski
prolazi confirm/reject (odbačen, eksplicitno testirano da NE prolazi),
puna audit DB tabela u ovom zadatku (odbačena, ide u DENT-IMPROVE-014).

## Rollback

`alembic downgrade -1` (provjereno, čisto). Kod-nivo: `git checkout` na
izmijenjene/nove fajlove iz radnog stabla (nema commit-a, ništa nije
pushovano/mergovano).

## Otvoreno za review

- Codex (Reviewer 1, obavezan) + Pi ili Crush (Reviewer 2) — standardan
  HIGH proces, dva nezavisna reviewera za auth/RBAC/token logiku.
- Fokus po kontraktu: Argon2id stvarno korišten (potvrđeno —
  `$argon2id$` prefiks), generička login greška (potvrđeno testom),
  ADMIN stvarno NE prolazi (potvrđeno testom za sva tri endpointa),
  lozinka/token se nigdje ne loguje (potvrđeno testom + grep), CSRF/cookie
  obrazloženje stvarno tačno (potvrđeno grep-om iznad), audit-granica
  jasno dokumentovana kao van obima.
- **HTTPS** ostaje deployment preduslov za `DENT-IMPROVE-015` (production
  gate) — nije riješeno ovdje, po dizajnu.
- CI `argon2-cffi`/`psycopg2-binary` gap (vidi OUT_OF_SCOPE_FINDING) treba
  riješiti prije nego ova grana ide kroz CI.
