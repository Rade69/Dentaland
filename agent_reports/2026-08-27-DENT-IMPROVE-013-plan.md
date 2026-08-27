---
task_id: DENT-IMPROVE-013
risk: HIGH
implementer: claude
reviewers: [codex, pi]
status: PLAN
created_at: 2026-08-27
---

# Plan — DENT-IMPROVE-013: Autentifikacija + RBAC

## Cilj

Individualni korisnički nalozi (Argon2id hash), server-side sesije (isti
sigurni token obrazac kao planirani cancel-link token: `secrets.token_urlsafe(32)`,
SHA-256 hash u bazi, `hmac.compare_digest`, `expires_at` + eksplicitna
invalidacija), i RBAC provjera (`RECEPTION`-only) na tri postojeća
nezaštićena staff endpointa (`GET /api/booking-requests`, `POST .../confirm`,
`POST .../reject`).

## Pogođeno

- `src/dentaland/models.py` — dodati `User`, `UserRole` (enum), `Session`
  (SAMO dodati, ne dirati `Appointment`/`Doctor`/itd.)
- `src/dentaland/services/auth.py` (novo) — hash/verify password,
  create/validate/invalidate session, `authenticate_user`, promjena
  lozinke sa invalidacijom svih sesija
- `backend/main.py` — `POST /api/auth/login`, `POST /api/auth/logout`,
  `CurrentUserDep`, `require_role([...])`, primijeniti na tri postojeća
  endpointa
- Nova Alembic migracija, `down_revision = d4e5f6a7b8c9` (potvrđen head
  sa `alembic heads` — vidi ispod)
- `scripts/create_user.py` (novo) — interaktivan CLI, `getpass`
- `pyproject.toml` — `argon2-cffi` dependency
- `tests/test_auth.py` (novo) — svi scenariji iz kontrakta
- `tests/test_backend.py` — **nužna posljedica, ne proširenje obima**:
  postojeći testovi za `confirm`/`reject`/`GET pending` trenutno pozivaju
  te endpointe bez autentifikacije. Pošto ovaj zadatak upravo te
  endpointe štiti sa `require_role(["RECEPTION"])`, ti pozivi bi počeli
  vraćati 401 umjesto 204/200 — acceptance kriterijum "postojeći pytest
  ostaje čist" bi bio nemoguć bez dodavanja login koraka (fixture koja
  kreira `RECEPTION` korisnika i loguje se) u te specifične testove.
  Mijenjaju se SAMO pogođeni testovi (dodaje se `authenticated_client`
  fixture), poslovna logika/assercije ostaju iste.

## Provjere prije pisanja koda

- `alembic heads` → `d4e5f6a7b8c9 (head)` — potvrđeno, poklapa se sa
  kontraktom.
- Baseline: `pytest tests/ -q` → 374 passed, 2 skipped (čisto).
  `ruff check src/dentaland tests backend` → čisto (`scripts/coordination.py`
  ima 5 pre-existing grešaka, van allowed_paths, ne dirati).
  `mypy src/dentaland backend` → čisto (17 fajlova).
  `agent_sensors.py --all` → 0 blocking findings.
- Grep potvrda (za CSRF odluku): nema `httpx`/`requests`/`QNetworkAccessManager`
  poziva bilo gdje u `desktop/**`; `web/app.js` zove SAMO
  `POST /api/booking-requests` (javni endpoint, ne staff). Nema
  browser-based staff klijenta koji bi mogao slati cross-origin zahtjeve
  na tri zaštićena endpointa.
- `python -c "import argon2"` → nedostaje, instaliran `argon2-cffi` u
  lokalno okruženje (biće i u `pyproject.toml`).

## Tehnička odluka: cookie-based sesija

Biram `HttpOnly`+`Secure`+`SameSite=Strict` cookie (ne `Authorization:
Bearer` header). Razlog: staff endpointi u ovom obimu nemaju JS klijenta
koji bi morao ručno rukovati tokenom (nema admin web panela) — cookie
automatizuje slanje na svaki naredni zahtjev bez dodatnog koda na
klijentskoj strani, kad taj klijent jednom postoji. `HttpOnly` sprečava
XSS-eksfiltraciju tokena (bitno jer JS ne treba pristup tokenu ni u kom
scenariju ovog obima).

**CSRF odluka**: `SameSite=Strict` bez punog CSRF token mehanizma je
dovoljna ZA SADA — potvrđeno grep-om (gore) da ne postoji nijedan
cross-origin browser-based staff klijent u trenutnom kodu koji bi CSRF
napad mogao iskoristiti. Ovo je svjesna, dokumentovana odluka, ne
prećutno izostavljena zaštita — ako se doda admin web panel u budućnosti,
CSRF token mehanizam mora biti dodat tada.

**Test posljedica**: `SameSite=Strict` + `Secure=True` cookie se, po
RFC 6265 semantici koju httpx/`http.cookiejar` poštuje, NE šalje nazad
klijentu na `http://` vezi. `TestClient` mora koristiti
`base_url="https://testserver"` (ASGI transport ne pravi stvarnu TLS
konekciju, samo scheme string) da bi httpx cookie jar prihvatio i vratio
`Secure` kolačić — standardan obrazac za testiranje secure cookieja kroz
Starlette `TestClient`.

## Šta NE dirati

- `desktop/**`, `web/**` — netaknuto.
- `src/dentaland/services/availability.py`, `booking.py`, `requests.py` —
  auth ide kao wrapper na routeru (FastAPI dependency), ne dira poslovnu
  logiku unutar tih servisa.
- Postojeći `migrations/versions/*.py`, `migrations/env.py`, `alembic.ini`.
- `scripts/migrate_sqlite_to_postgres.py`.
- Ne graditi OAuth/SSO/2FA, ne graditi punu audit DB tabelu (ide u
  DENT-IMPROVE-014) — login pokušaji idu SAMO u `logging` modul.
- Ne dirati `scripts/coordination.py` (pre-existing ruff nalazi, van
  allowed_paths).

## Plan verifikacije

1. `pytest tests/ -q` (pun suite, uključujući novi `test_auth.py` i
   ažurirani `test_backend.py`).
2. `ruff check src/dentaland tests backend scripts/create_user.py`.
3. `mypy src/dentaland backend` (baseline provjera — 0 grešaka prije i
   poslije).
4. `python scripts/agent_sensors.py --all`.
5. Ručna alembic upgrade/downgrade provjera nove migracije na privremenoj
   SQLite bazi.
6. Spot-check grep kroz diff za `password`/`token` u blizini `log`/`print`
   poziva — potvrditi da se nigdje ne loguje osjetljiva vrijednost.

## Rollback

`alembic downgrade -1` briše `sessions`/`users` tabele (nove, prazne pri
uvođenju — bez gubitka postojećih podataka). Kod-nivo rollback: `git
checkout` na fajlove iz `allowed_paths` (grana se ne mergaš dok review ne
prođe).

## Odbačene opcije

**Opcija A (odbačena): `Authorization: Bearer` header umjesto cookie.**
Razmatrano jer izbjegava CSRF pitanje u potpunosti. Odbačeno jer bi
zahtijevalo da budući klijent (kad god se pojavi) ručno čuva/šalje token
na svaki zahtjev — cookie je manje trenja za taj budući rad, a CSRF rizik
je već eliminisan (nema cross-origin staff klijenta) pa dodatna
kompleksnost bearer pristupa (ručno rukovanje tokenom, nema
brauzer-nativne zaštite od XSS eksfiltracije jer bi token vjerovatno
završio u `localStorage`) nije opravdana.

**Opcija B (odbačena): ADMIN automatski prolazi `confirm`/`reject`.**
v3.1 eksplicitno: administrator sistema ne dobija automatski pravo na
operativne radnje van administracije. Test eksplicitno provjerava da
`ADMIN` dobija 403 (ne "ADMIN je valjda i RECEPTION").

**Opcija C (odbačena): puna audit DB tabela u ovom zadatku.** Van obima
(DENT-IMPROVE-014) — ovaj zadatak piše samo u `logging`, ne u novu
tabelu, po Radovanovoj odluci #3 (kontrakt).
