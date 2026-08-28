# DENT-IMPROVE-014B — Plan (prije koda)

## Cilj

`LOGIN_SUCCESS` (sa tačnim `actor_user_id`) i `LOGIN_FAILURE` (sa
`actor_user_id=NULL`) audit zapisi u `audit_events`, uz `source_ip` iz
stvarnog HTTP zahtjeva, dodani POREDO sa postojećim `logger.info(...)`
pozivima u `authenticate_user` — bez brisanja logginga.

## Pogođeno

- `src/dentaland/services/auth.py` — `authenticate_user` dobija opcioni
  keyword-only `source_ip: str | None = None` parametar (default ne mijenja
  postojeće pozivaoce); dva `write_audit_event(...)` poziva dodana pored
  postojećih `logger.info(...)` na oba mjesta (neaktivan/nepostojeći
  korisnik, pogrešna lozinka, uspjeh).
- `backend/main.py` — `login()` route handler prosljeđuje
  `source_ip=request.client.host if request.client else None` u
  `authenticate_user(...)`. Nema drugih izmjena u `main.py`.
- `tests/test_auth.py` — dopuna novim testovima za audit zapise (uspjeh,
  dva neuspjeh scenarija, source_ip popunjen, spot-check da lozinka nije u
  `metadata_minimal`).

## Odluka: gdje ide audit poziv

Unutar `authenticate_user` (ne u route handleru) — tačno mjesto gdje već
postoje oba `logger.info(...)` poziva, minimalna izmjena, jedan izvor
istine za "šta se desilo pri loginu". `source_ip` dolazi kao parametar jer
`auth.py` nema pristup `Request` objektu (FastAPI-specifičan tip, servisni
sloj ostaje framework-agnostičan).

## Odluka: `LOGIN_FAILURE` `metadata_minimal`

**Odluka: uključiti pokušani `username`** (`metadata={"username": username}`).

Razlozi:
- `actor_user_id=NULL` već je primarna user-enumeration zaštita na audit
  nivou (isto kao HTTP response) — `metadata_minimal` je interni
  compliance/security zapis, ne nešto vraćeno napadaču, pa dodatni
  username tu ne otvara novi enumeration kanal prema vanjskom svijetu.
- Korisno za istragu brute-force obrazaca (koji username-ovi se
  pokušavaju, sa koje IP adrese).
- Postojeći `logger.info("LOGIN_FAILURE username=%r", username)` već
  bilježi isti podatak na istom mjestu (DENT-IMPROVE-013, Radovanova
  odluka) — ovo ne uvodi novu vrstu izloženosti, samo duplira već
  prihvaćen podatak u trajniju tabelu.

Poznat, prihvaćen rubni slučaj (nasljeđen iz DENT-IMPROVE-013, ne nov u
ovom tasku): ako korisnik greškom upiše lozinku u polje za username,
taj tekst će se pojaviti i u logu i u `metadata_minimal`. Isti rizik već
postoji u produkciji od DENT-IMPROVE-013 (logger.info) — ovaj task ga ne
uvodi, samo ga replicira u audit tabelu. Ne rješavamo ga ovdje (van
scope-a — zahtijevalo bi heuristiku "izgleda kao lozinka" koja nije
tražena u kontraktu).

`LOGIN_SUCCESS` dobija `resource_type="user", resource_id=user.id` (jasna
veza na pogođeni resurs, bez dodatnog rizika — nema tajnih podataka).

## Šta NE dirati

- `src/dentaland/models.py`, `src/dentaland/services/audit.py` (jezgro).
- `src/dentaland/services/appointments.py` (DENT-IMPROVE-014C).
- `desktop/**`, `web/**`, `migrations/**`.
- Postojeći `logger.info(...)` pozivi u `auth.py` — ne brišu se.
- `CHANGE_ROLE` — ostaje dormant, nema novog koda oko nje.

## Plan verifikacije

- `pytest tests/ -q` (pun paket, uključujući postojeći `test_auth.py`
  suite).
- `ruff check .`
- `mypy src/ backend/` (ili projektna mypy komanda ako postoji drugačija).
- `python scripts/agent_sensors.py --all` (ako postoji u ovom worktree-u).
- Ručna provjera: novi testovi upisuju red u `audit_events` sa očekivanim
  `action`/`actor_user_id`/`source_ip`, i da `tajna-lozinka-xyz` string
  nikad nije u `metadata_minimal` koloni.

## Rollback

Izmjena je aditivna i lokalizovana na dva fajla (`auth.py` signature +
dva poziva, `main.py` jedan keyword argument) — rollback je
`git checkout -- src/dentaland/services/auth.py backend/main.py
tests/test_auth.py` unutar ovog worktree-a, bez uticaja na `main` (ništa
nije mergovano).

## Odbačene opcije

- Audit poziv u `backend/main.py` route handleru umjesto u
  `authenticate_user`: odbačeno — razdvojilo bi mjesto gdje se
  "šta se desilo" odlučuje (auth.py) od mjesta gdje se to bilježi
  (main.py), i zahtijevalo bi da `login()` hendluje i success i exception
  granu da bi upisao oba ishoda (duplirana logika oko `try/except` koja
  već postoji za `AuthenticationError`).
- Prosljeđivanje `session=` u `write_audit_event`: odbačeno — login audit
  nema okolnu transakciju (kontrakt eksplicitno kaže da ovo nije
  potrebno), samostalni mod (bez `session=`) je tačan izbor.
- Prazan `metadata_minimal` za `LOGIN_FAILURE`: razmotreno, odbačeno —
  vidi obrazloženje iznad (isti podatak već je u logu, nema novog
  enumeration kanala prema vanjskom svijetu jer audit tabela nije javno
  izložena).
