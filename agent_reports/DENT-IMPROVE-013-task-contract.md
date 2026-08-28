---
task_id: DENT-IMPROVE-013
risk: HIGH
implementer: claude
reviewers: [codex, pi]
status: "DONE — MERGED u main (merge commit da67027, 27.8.2026). Individualni nalozi (Argon2id), server-side sesije, RBAC (RECEPTION-only) na tri ranije nezaštićena endpointa. Fix runda 1 (Codex F1, HIGH): change_password nije bio atomski sa opozivom sesija. Review: Codex+Pi+Crush (svi PASS_WITH_NOTES). Radovan human approval 27.8.2026. Otvara DENT-IMPROVE-014."
created_at: 2026-08-27
---

# DENT-IMPROVE-013 — Autentifikacija + RBAC

## Kontekst

`docs/DENTALAND_IMPROVEMENT_BACKLOG.md` sekcija 14 — HIGH, tip security,
sad jedini neblokiran Prioritet C task (`DENT-IMPROVE-012` DONE, merge
`824590f`, 27.8.2026). `DENT-IMPROVE-014` (audit) i `DENT-IMPROVE-015`
(production gate) čekaju ovaj task.

**Izvor istine za tehničke sigurnosne detalje:**
`docs/dentaland-razvojni-plan-v3.1.md`, sekcija "Autentifikacija i sesije"
(linija ~261) i "RBAC" (linija ~253) — ovaj dokument ima prednost nad
backlog opisom kad se razlikuju. Ključni citat:

> Argon2id (ili trenutno preporučen ekvivalent) za password hash, HTTPS
> obavezno, secure/HttpOnly/SameSite cookie ako se koristi cookie session,
> CSRF zaštita gdje je relevantna, login rate limiting, session
> expiration, invalidacija sesija poslije promjene lozinke, bez
> zajedničkog `admin` naloga za više zaposlenih — svaki zaposleni svoj
> nalog (audit ima smisla samo tako).

I RBAC semantika (v3.1, ne samo nabrajanje uloga):

- **RECEPTION** — vidi raspored, kreira/mijenja/otkazuje termin, vidi
  osnovne kontakt podatke, NEMA pristup detaljnoj medicinskoj
  dokumentaciji.
- **DENTIST** — vidi raspored, vidi podatke potrebne za pružanje usluge,
  pristupa medicinskim podacima gdje su implementirani i potrebni.
- **ADMIN** — administrira korisnike/konfiguraciju/sistem; **ne dobija
  automatski pravo da čita medicinski sadržaj samo zato što je
  administrator sistema**.
- "Permission check na nivou endpointa/servisa. **UI skrivanje nije
  sigurnosna kontrola.**"

## Trenutno stanje repoa (provjereno 27.8.2026, prije pisanja kontrakta)

- `backend/main.py` ima 4 endpointa: `POST /api/booking-requests` (javni
  submit, ima svoj `@limiter.limit("10/minute")`), i **tri potpuno
  nezaštićena staff-only endpointa**: `GET /api/booking-requests` (lista
  zahtjeva, linija 151), `POST .../confirm` (linija 166),
  `POST .../reject` (linija 186). Trenutno bilo ko ko dopre do backenda
  može odobriti/odbiti bilo koji zahtjev bez ikakve autentifikacije.
- **Nijedan postojeći klijent trenutno stvarno ne zove ta tri staff
  endpointa.** Desktop app (PySide6) radi direktno preko SQLAlchemy nad
  lokalnim SQLite-om (Faza 0 arhitektura, `CLAUDE.md`), NE zove backend
  API uopšte (potvrđeno grep-om — nema `httpx`/`requests` poziva u
  `desktop/`). `web/app.js` (javna forma) zove samo `POST
  /api/booking-requests`. Ta tri staff endpointa su ranije napravljena
  "unaprijed", bez stvarnog konzumenta.
- **Nema nikakvog `User`/`Account`/`Role` modela** u `src/dentaland/models.py`.
  Nema password hashing biblioteke, JWT/session biblioteke u
  `pyproject.toml`.
- Postojeći DI obrazac u `backend/main.py`:
  `XxxDep = Annotated[Type, Depends(get_xxx)]` (vidi `SessionFactoryDep`,
  linija 97) — nova auth zavisnost treba pratiti isti obrazac
  (`CurrentUserDep`, `require_role(...)`).
- `src/dentaland/services/` sadrži servisni sloj (`requests.py`,
  `availability.py`, itd.) — poslovna logika ide tu, ne u `backend/main.py`
  direktno (`CLAUDE.md` arhitektura).
- Postojeći siguran token obrazac (već uspostavljen za buduće cancel-link
  tokene, `CLAUDE.md`): `secrets.token_urlsafe(32)`, SHA-256 hash u bazi
  (nikad plaintext), `hmac.compare_digest()` za poređenje, `expires_at` +
  jednokratna/invalidaciona semantika. **Session token ide istim
  obrascem.**

## Radovanove odluke (27.8.2026, prije pisanja kontrakta)

1. **Kreiranje naloga: CLI skripta, ne UI.** Nema signup ekrana u ovom
   tasku — nema još stvarnog staff-facing klijenta koji bi ga koristio
   (desktop ne zove backend, nema admin web panela). `scripts/create_user.py`
   (interaktivan, `getpass` za lozinku — NIKAD lozinka kao CLI argument,
   curi kroz shell history/process listu).
2. **`confirm`/`reject` endpoint: SAMO `RECEPTION` uloga.** Eksplicitno
   NE `ADMIN` automatski (v3.1: "ADMIN ne dobija automatski" privilegije
   van administracije sistema), NE `DENTIST`. `GET /api/booking-requests`
   (lista pending) prati istu logiku — `RECEPTION`-only (isti radni tok
   kao confirm/reject).
3. **Audit granica: obično strukturirano logovanje sada, prava audit
   tabela u `DENT-IMPROVE-014`.** v3.1 navodi `LOGIN_SUCCESS`/
   `LOGIN_FAILURE` kao audit događaje (P1.8, HIGH), ali append-only audit
   infrastruktura je eksplicitno sljedeći task. Ovaj task piše login
   pokušaje (uspjeh/neuspjeh, username, timestamp, **NIKAD lozinku ili
   token**) u standardni Python `logging` modul, NE u novu DB tabelu.
   `DENT-IMPROVE-014` kasnije gradi pravu append-only tabelu za sve akcije
   (ne samo login) — ovaj task ne smije otežati taj budući rad (npr. ne
   raštrkati login-logiku na način koji bi spriječio kasnije ubacivanje
   audit poziva na jednom mjestu).

## Cilj

Individualni korisnički nalozi sa Argon2id password hashingom, server-side
sesije (isti sigurni token obrazac kao postojeći cancel-token dizajn), i
RBAC provjera na tri postojeća nezaštićena staff endpointa — bez
uvođenja OAuth/SSO/2FA/pune audit infrastrukture (sve eksplicitno van
obima, vidi ispod).

## Required scope

1. **Novi modeli** u `src/dentaland/models.py`:
   - `User`: `id`, `username` (unique), `password_hash`, `role`
     (`Enum(RECEPTION|DENTIST|ADMIN, native_enum=False)` — isti obrazac
     kao postojeći `AppointmentStatus`), `is_active` (bool, default
     `True`), `created_at` (`TZDateTime`).
   - `Session`: `id`, `user_id` (FK → `users.id`), `token_hash` (unique,
     SHA-256 hex), `expires_at` (`TZDateTime`), `created_at`
     (`TZDateTime`), `revoked_at` (nullable `TZDateTime` — eksplicitna
     invalidacija, ne brisanje reda).
2. **`src/dentaland/services/auth.py`** (novo) — poslovna logika, ne u
   routeru:
   - `hash_password`/`verify_password` (Argon2id, preko `argon2-cffi`).
   - `create_session`/`validate_session`/`invalidate_session` — token
     generisan `secrets.token_urlsafe(32)`, hash čuvan, `hmac.compare_digest`
     za validaciju, provjera `expires_at` i `revoked_at`.
   - `authenticate_user` — generička greška na pogrešan username ILI
     pogrešnu lozinku (ne otkrivati koji je slučaj — sprečava user
     enumeration).
   - Invalidacija SVIH postojećih sesija korisnika pri promjeni lozinke
     (v3.1 eksplicitan zahtjev) — funkcija za promjenu lozinke je dio
     ovog servisa čak i ako nema endpoint za nju u ovom tasku (CLI
     skripta je poziva direktno).
3. **`backend/main.py` (ili novi `backend/auth_routes.py`, implementer
   bira i dokumentuje):**
   - `POST /api/auth/login` — **sopstveni, odvojen rate limit** (v3.1:
     "odvojeni limiti minimalno za... login" — NE dijeliti kvotu sa
     `/api/booking-requests`), npr. `@limiter.limit("5/minute")`.
     Postavlja session cookie (`HttpOnly`, `Secure`, `SameSite=Strict`)
     ako implementer bira cookie-based sesiju (vidi tehnička napomena
     ispod).
   - `POST /api/auth/logout` — invalidira trenutnu sesiju.
   - `CurrentUserDep`/`require_role(["RECEPTION"])` FastAPI zavisnosti
     (isti `Annotated[Type, Depends(...)]` obrazac kao `SessionFactoryDep`).
   - Primijeniti `require_role(["RECEPTION"])` na `GET
     /api/booking-requests`, `POST .../confirm`, `POST .../reject`.
   - Login pokušaji (uspjeh/neuspjeh) idu u `logging` modul — username,
     ishod, timestamp. NIKAD lozinka, token, ili cookie vrijednost.
4. **Alembic migracija** (novo, `down_revision = d4e5f6a7b8c9`) — kreira
   `users` i `sessions` tabele.
5. **`scripts/create_user.py`** (novo) — interaktivan CLI, `getpass` za
   lozinku, kreira `User` red sa Argon2id hash-om.
6. **`pyproject.toml`** — dodati `argon2-cffi` dependency.
7. **Testovi** (`tests/test_auth.py`, novo):
   - login uspjeh (validni kredencijali) → sesija kreirana.
   - login neuspjeh (pogrešna lozinka / nepostojeći username) → generička
     greška, isti status/poruka za oba slučaja.
   - neautentifikovan poziv na `GET/confirm/reject` → 401.
   - autentifikovan ali pogrešna uloga (npr. `DENTIST` zove `confirm`) →
     403.
   - `RECEPTION` uspješno zove `confirm`/`reject`/`GET pending`.
   - `ADMIN` zove `confirm` → 403 (eksplicitno, ne pretpostaviti da ADMIN
     "naravno" prolazi).
   - logout invalidira sesiju (sljedeći poziv sa istim tokenom → 401).
   - rate limit na `/api/auth/login` (odvojen od booking-request limita).
   - promjena lozinke invalidira SVE postojeće sesije tog korisnika.
   - spot-check: lozinka/token se NIKAD ne pojavljuju u response body-ju
     ni u uhvaćenom log izlazu.

## Tehnička napomena — cookie vs bearer token (implementer odlučuje, dokumentuje)

v3.1 pominje cookie-based sesiju kao referentni obrazac ("secure/HttpOnly/
SameSite cookie **ako** se koristi cookie session"), ali ne nalaže ga kao
jedinu opciju. Implementer bira cookie (`HttpOnly`+`Secure`+`SameSite=Strict`)
ili `Authorization: Bearer <token>` header i **dokumentuje razlog** u
izvještaju — isti obrazac kao psycopg driver izbor u `DENT-IMPROVE-012`.

**CSRF:** v3.1 traži CSRF zaštitu "gdje je relevantna". Trenutno ne
postoji nijedan browser-based staff klijent koji bi slao cross-origin
zahtjeve na ove endpointe (desktop ne zove backend, nema admin web
panela) — ako implementer bira cookie sesiju sa `SameSite=Strict`, to je
dovoljna odbrana ZA SADA (nema cross-origin vektora da se iskoristi), ALI
ovo mora biti eksplicitno dokumentovano kao svjesna odluka (ne prećutno
izostavljen CSRF token mehanizam) — reviewer provjerava da je
obrazloženje stvarno tačno (da zaista ne postoji cross-origin staff
klijent u trenutnom kodu).

## Critical constraints (v3.1 + CLAUDE.md)

- **Argon2id, ne bcrypt/MD5/SHA-only.** v3.1 eksplicitno traži Argon2id.
- **Nikad log lozinku, cookie, token** (v3.1, CLAUDE.md princip #2 iz
  "Never" liste) — ni u aplikacionom logu, ni u exception traceback-u, ni
  u test output-u koji bi mogao završiti u CI logu.
- **Bez zajedničkog admin naloga.** Svaki zaposleni svoj `User` red.
- **Generička login greška** — ne otkrivati da li je username ili
  lozinka pogrešna (user enumeration zaštita).
- **Session invalidacija poslije promjene lozinke** — v3.1 eksplicitan
  zahtjev, testirati stvarno, ne pretpostaviti.
- **UI skrivanje nije sigurnosna kontrola** — provjera mora biti na
  nivou endpointa/servisa (FastAPI dependency), ne nešto što se
  "provjerava" samo u budućem frontend kodu.
- **2FA, OAuth, SSO, enterprise IAM — eksplicitno van obima** (backlog +
  v3.1: "2FA nije obavezan MVP uslov").
- **Puna audit tabela (P1.8) — van obima**, ide u `DENT-IMPROVE-014` (vidi
  Radovanova odluka #3 gore). Ovaj task piše samo `logging`, ne DB tabelu.
- **HTTPS** je deployment/infrastrukturni preduslov (v3.1), ne nešto što
  se implementira u ovom tasku (lokalni dev/test rad je i dalje HTTP) —
  napomenuti u izvještaju kao otvorenu produkcijsku zavisnost za
  `DENT-IMPROVE-015` (production gate), ne riješiti ovdje.
- Ne diraj Windows `postgresql-16` servis na portu 5432
  (`deklarant_pro`) — koristi izolovanu Dentaland instancu (port 5433,
  `.env`) za bilo kakvo Postgres testiranje ako implementer odluči
  testirati auth i nad Postgres dijalektom (opciono, nije obavezno za
  ovaj task — SQLite testovi su dovoljni za acceptance).

## Acceptance criteria

- [ ] neautentifikovan poziv na sva tri staff endpointa vraća 401
- [ ] autentifikovan korisnik pogrešne uloge vraća 403 (testirano za
      `DENTIST` i `ADMIN`, ne samo "nepostojeći korisnik")
- [ ] `RECEPTION` uloga uspješno prolazi kroz sva tri endpointa
- [ ] lozinke su Argon2id hash, nikad plaintext u bazi
- [ ] login koristi generičku grešku (ne otkriva username vs lozinka)
- [ ] login ima sopstveni rate limit, odvojen od booking-request limita
- [ ] sesija ima expiration i invalidira se na logout
- [ ] promjena lozinke invalidira sve postojeće sesije tog korisnika
- [ ] nijedna lozinka/token se ne pojavljuje u logovima/response-ima
      (provjereno testom, ne samo pregledom koda)
- [ ] `scripts/create_user.py` radi, ne prima lozinku kao CLI argument
- [ ] postojeći `pytest tests/ -q`, `ruff`, `mypy`, `agent_sensors.py --all`
      ostaju čisti
- [ ] `desktop/**` i `web/**` netaknuti (ovaj task ne dira klijente, samo
      backend API sloj)
- [ ] nema nove DB audit tabele (van obima, ide u 014)

## Allowed paths

```text
src/dentaland/models.py                  (SAMO dodati User/Session, ne dirati postojeće tabele)
src/dentaland/services/auth.py           (novo)
backend/main.py                          (ili novi backend/auth_routes.py, implementer bira)
migrations/versions/*.py                 (SAMO nova migracija, down_revision=d4e5f6a7b8c9)
scripts/create_user.py                   (novo)
pyproject.toml                           (dodati argon2-cffi)
tests/test_auth.py                       (novo)
agent_reports/**
docs/DENTALAND_IMPROVEMENT_BACKLOG.md    (samo status napomena na kraju, ne mijenjati opis obima)
```

## Forbidden paths

```text
desktop/**                               (ovaj task ne dira desktop klijent)
web/**                                   (javna forma ostaje nepromijenjena/neautentifikovana, namjerno)
src/dentaland/services/availability.py
src/dentaland/services/booking.py
src/dentaland/services/requests.py       (READ-ONLY referenca — auth ide kao wrapper na routeru, ne mijenja poslovnu logiku unutra)
migrations/versions/**                   (postojeći fajlovi, osim nove migracije)
migrations/env.py
alembic.ini
scripts/migrate_sqlite_to_postgres.py
```

## Review

Standardan HIGH proces — v3.1 eksplicitno zahtijeva **dva nezavisna
reviewera** za promjene auth/RBAC/token logike (isto što CLAUDE.md/
`docs/dentaland-agentski-razvoj.md` već nalažu za HIGH). Codex (Reviewer 1,
obavezan) + Pi ili Crush (Reviewer 2). Implementer Claude, u svom
worktree-u, review u nezavisnoj sesiji.

Reviewer posebno provjerava:

- Argon2id stvarno korišten (ne slučajno bcrypt/passlib default koji
  odstupa od v3.1 zahtjeva).
- Generička login greška — pokušati oba scenarija (nepostojeći username,
  pogrešna lozinka) i potvrditi identičan response.
- Da `ADMIN` uloga STVARNO ne prolazi na `confirm`/`reject` (lako je
  slučajno dodati "ADMIN uvijek prolazi" bypass logiku — eksplicitno
  provjeriti da nije tu).
- Da se lozinka/token stvarno nigdje ne loguje — grep kroz cijeli diff za
  `password`/`token` u blizini `log`/`print` poziva.
- Da CSRF/cookie odluka ima realno tačno obrazloženje (provjeriti da
  zaista nema cross-origin staff klijenta u trenutnom kodu, ne samo
  preuzeti implementerovu tvrdnju).
- Da audit-granica (logging umjesto DB tabele) nije prerasla u prećutno
  "audit je gotov" – izvještaj mora eksplicitno reći da je puna tabela
  van obima, ide u 014.

## Koordinacija

Nema paralelnih zadataka trenutno aktivnih na ovim putanjama.

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-013 --agent claude --paths src/dentaland/models.py,src/dentaland/services/auth.py,backend/main.py,pyproject.toml
```

prije početka rada.

## Plan prije izmjene (HIGH — obavezno prije editovanja)

Implementer piše kratak plan (Cilj / Pogođeno / Plan / Šta NE dirati /
Plan verifikacije / Rollback / Odbačene opcije) u `agent_reports/` PRIJE
prve izmjene koda, po istom obrascu kao `DENT-IMPROVE-012`.
