# DENT-IMPROVE-013 — Codex independent review

```yaml
verdict: REJECT
scope: PASS
acceptance: FAIL
architecture: PASS_WITH_NOTES
security: FAIL
blocking_findings:
  - id: F1
    severity: HIGH
    title: Promjena lozinke i opoziv sesija nisu atomski
```

## CILJ

Nezavisno provjeriti Argon2id autentifikaciju, server-side session tok,
RECEPTION-only RBAC, zaštitu tajni, cookie/CSRF odluku i Alembic migraciju.

Review je urađen nad eksplicitno predatim nekomitovanim snapshotom grane
`task/DENT-IMPROVE-013-auth-rbac`.

## BLOCKING FINDING

### F1 — HIGH: promjena lozinke može ostaviti sve stare sesije validnim

**Zahtjev:** v3.1 i Task Contract eksplicitno zahtijevaju invalidaciju svih
postojećih sesija poslije promjene lozinke.

**Dokaz:** `src/dentaland/services/auth.py::change_password` mijenja hash i
odmah ga commit-uje u jednoj ORM sesiji. Tek nakon zatvaranja te transakcije
poziva `invalidate_all_sessions_for_user`, koji otvara drugu transakciju i
posebno commit-uje `revoked_at` vrijednosti.

Adversarna in-memory proba simulirala je kvar revoke koraka nakon prvog
commita. Stvarni rezultat:

```text
ERROR=RuntimeError
NEW_PASSWORD_COMMITTED=True
OLD_SESSION_STILL_VALID=True
```

**Failure path:** privremeni DB/connection/commit problem u drugom koraku,
prekid procesa ili drugi izuzetak nastane nakon što je novi password hash već
trajno upisan. Pozivalac dobije grešku, ali stare cookie sesije ostanu važeće.

**Uticaj:** reset/promjena kompromitovane lozinke ne prekida pristup napadaču
koji već posjeduje session token. To direktno ruši sigurnosni invariant zbog
kojeg je invalidacija unesena u obavezni scope.

**Minimalni smjer popravke:** hash promjena i opoziv svih session redova moraju
biti dio iste DB transakcije i jednog commita; na bilo kojem kvaru oba dijela
se rollbackuju. Dodati test koji izazove grešku prije commita/opoziva i
potvrđuje da nije moguće stanje „nova lozinka + stare validne sesije“.

## POTVRĐENO ISPRAVNO

### Auth i RBAC

- `PasswordHasher()` iz `argon2-cffi` koristi Argon2id; testovi i runtime
  potvrđuju login/hash tok.
- Pogrešna lozinka i nepostojeći username vraćaju isti status i isti JSON;
  neaktivan nalog takođe ne otkriva poseban razlog.
- Dummy Argon2 verifikacija se izvršava kad korisnik ne postoji.
- Sva tri staff endpointa koriste jedan `RequireReceptionDep` gate.
- `DENTIST` i `ADMIN` dobijaju 403; nema „ADMIN uvijek prolazi“ grane.
- Neautentifikovan korisnik dobija 401, a RECEPTION prolazi kroz GET,
  confirm i reject.
- Login limit je 5/minute i odvojen je od javnog booking-request limita.
- Logout i normalni happy-path password-change test invalidiraju sesije;
  F1 se odnosi na transakcijski failure path koji postojeći test ne pokriva.

### Token, cookie i logovi

- Session token nastaje preko `secrets.token_urlsafe(32)`; baza čuva samo
  SHA-256 hash. `hmac.compare_digest` postoji u validation toku.
- Cookie ima `HttpOnly`, `Secure` i `SameSite=Strict`; token nije u JSON
  response body-ju.
- Pretraga diff-a i cijelog relevantnog koda nije našla password/token/cookie
  vrijednost u `logger`/`print` pozivima. Login loguje samo ishod i username;
  `%r` sprečava newline log-injection kroz username.
- Nezavisna pretraga `desktop/**` nije našla HTTP staff klijent. `web/app.js`
  i Playwright koriste samo javni `POST /api/booking-requests`; nema poziva na
  auth, pending, confirm ili reject staff tok. Zato je dokumentovano
  SameSite-only CSRF obrazloženje tačno za trenutno stanje i ugovoreni scope.
  Prije budućeg browser staff klijenta CSRF odluka mora ponovo na review.

### Migracija i scope

- Nova migracija ima `down_revision = d4e5f6a7b8c9`; `alembic heads` daje
  `e5f6a7b8c9d0 (head)`.
- Nezavisni disposable SQLite upgrade do head-a kreirao je `users` i
  `sessions`; downgrade `-1` uklonio je obje, uz očuvanje svih pet postojećih
  poslovnih tabela.
- Nema audit DB tabele; `LOGIN_SUCCESS`/`LOGIN_FAILURE` ostaju standardni
  logging događaji, a puna audit infrastruktura ostaje DENT-IMPROVE-014.
- Forbidden `desktop/**`, `web/**`, tri postojeća servisa,
  `migrations/env.py`, `alembic.ini`, postojeće revisions i DENT-012 migrator
  nisu dirani.
- `.github/workflows/ci.yml` je van task allowed paths, ali je byte-diff
  identičan zasebno odobrenom main commitu `0c038d8`; ne predstavlja novu
  promjenu ovog snapshot reviewa.

## VERIFIKACIJA

- `pytest tests/test_auth.py -q`: **20 passed**.
- `pytest tests/ -q`: **394 passed, 2 skipped**, 12 warnings.
- `ruff check src/dentaland desktop backend tests scripts/create_user.py
  scripts/agent_sensors.py`: **All checks passed**.
- `mypy src/dentaland desktop backend`: **Success**, 53 source fajla.
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.

Zeleni suite ne mijenja F1 verdict: postojeći password-change test pokriva
samo slučaj u kojem oba odvojena commita uspiju.

## NE DIRATI

- Ne proširivati RBAC tako da ADMIN automatski dobije RECEPTION prava.
- Ne uvoditi signup UI, OAuth/SSO/2FA ili audit tabelu u ovaj fix.
- Ne dirati klijente, postojeće poslovne servise ni stare migracije.
- HTTPS ostaje obavezni DENT-IMPROVE-015 deployment gate.

## SLJEDEĆE

Verdikt je **REJECT** dok password hash promjena i opoziv svih sesija nisu
atomski i adversarno testirani. Poslije fix runde Codex ponavlja failure-path
mutaciju, auth suite i standardne gateove; tek zatim ide Reviewer 2 i Radovan
human approval.
