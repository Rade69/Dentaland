---
task_id: DENT-IMPROVE-013
risk: HIGH
reviewer: crush
role: Reviewer 2 (nezavisna provjera, fresh)
verdict: PASS_WITH_NOTES
date: 2026-08-27
---

# DENT-IMPROVE-013 — Crush nezavisan review (autentifikacija + RBAC)

Nezavisan pregled od nule. Nisam čitao Codex rezonovanje prije sopstvene
analize koda i verifikacija — Codex izvještaje (round1 REJECT, round2
PASS_WITH_NOTES) sam pročitao tek nakon što sam sam pregledao diff, pročitao
kod i pokrenuo sve gateove. Pi izvještaj ne postoji u worktree-u u trenutku
ovog reviewa (korisnikov brief je bio kopija Pi-bloka koji nije fizički
priložen — rekonstruisao sam obim iz Task Contract-a i izvještaja).

Napomena o svježini čitanja (lekcija iz DENT-IMPROVE-012): svi fajlovi su
pročitani U OVOJ sesiji neposredno prije pisanja, i `pytest` je pokrenut
NAKON čitanja — nema zastarjelog čitanja iz ranije faze sesije.

## Verdikt

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## Nalaz

### N1 (non-blocking, novi) — `tests/test_backend.py` i `tests/test_models.py` su izvan `allowed_paths` kontrakta

- Task Contract `allowed_paths` navodi SAMO `tests/test_auth.py` (novo) kao
  dozvoljen test fajl. `tests/test_backend.py` (+53) i `tests/test_models.py`
  (+11) su izmijenjeni, a NISU u toj listi.
- Zašto je to urađeno (i zašto je opravdano): zaštita tri staff endpointa
  (`require_role(["RECEPTION"])`) nužno mijenja njihovo ponašanje za
  postojeće neautentifikovane pozivaoce. Bez `reception_session` fixture u
  `test_backend.py` (6 testova za `GET /booking-requests`/`confirm`/`reject`),
  i bez proširenja `test_sve_tabele_su_kreirane` u `test_models.py` (test
  eksplicitno nabraja SVE tabele), acceptance kriterijum "postojeći pytest
  ostaje čist" bi bio nemoguć — ti testovi bi vratili 401 ili pali na novim
  tabelama.
- Implementer je ovo **transparentno dokumentovao** kao "nužne posledične
  izmjene (ne proširenje obima)" u izvještaju (sekcija "Nužne posledične
  izmjene"), nije prećutno proširio obim. Poslovna logika u tim fajlovima
  NIJE mijenjana — samo autentifikacijski preduslov dodat tamo gdje ga nova
  zaštita zahtijeva.
- Ovo je propust u Task Contract-u (preuska `allowed_paths` lista, za razliku
  od DENT-IMPROVE-012 gdje je `tests/test_backend.py` bio eksplicitno
  dozvoljen), ne implementerova greška. Ne blokira — nema produkcionog
  uticaja — ali treba biti vidljivo Radovanu pri human approval-u.

## Potvrđeno lično (ne iz izvještaja)

Sve komande pokrenute u worktree-u `task/DENT-IMPROVE-013-auth-rbac`.

| Provjera | Rezultat |
|---|---|
| `git diff --name-only` (tracked) | `ci.yml`, `backend/main.py`, `pyproject.toml`, `models.py`, `test_backend.py`, `test_models.py` |
| forbidden paths (`desktop/**`, `web/**`, `availability.py`, `booking.py`, `requests.py`, `migrations/env.py`, `alembic.ini`, `scripts/migrate_sqlite_to_postgres.py`) | **svi 0 changed** |
| `.env` | gitignored (`git check-ignore`) |
| `.github/workflows/ci.yml` vs `main` | **prazan diff** — identičan već-odobrenom `main` commit-u `0c038d8` ("fix(ci): dodati psycopg2-binary i argon2-cffi"), nije nova promena ovog reviewa |
| `alembic heads` | `e5f6a7b8c9d0 (head)` — jedan head, bez grananja, `down_revision = d4e5f6a7b8c9` |
| Argon2id prefiks | `$argon2id$...` (potvrđeno runtime); `verify_password` tačna→True, pogrešna→False |
| `ruff check src/dentaland desktop backend tests scripts/create_user.py scripts/agent_sensors.py` | **All checks passed** |
| `mypy src/dentaland desktop backend` | **Success: no issues found in 53 source files** |
| `python scripts/agent_sensors.py --all` | **0 blocking findings** |
| `pytest tests/ -q` | **395 passed, 2 skipped** (12 warnings) |
| `pytest tests/test_auth.py -q` (izolovano) | **21 passed** |
| grep `password`/`token`/`cookie` uz `logger`/`print` u auth.py/backend/create_user.py | **NEMA pogodaka** (osjetljivo se ne loguje) |
| grep cross-origin klijent u `desktop/**`/`web/**` | samo `web/app.js:211` → javni `POST /api/booking-requests`; nema staff HTTP klijenta |

## Potvrđeno čitanjem koda (ključne sigurnosne tačke iz kontrakta)

- **Argon2id, ne bcrypt/MD5**: `src/dentaland/services/auth.py` koristi
  `argon2.PasswordHasher()` (`$argon2id$` prefiks potvrđen runtime).
- **Generička login greška**: `authenticate_user` diže isti
  `AuthenticationError("pogrešno korisničko ime ili lozinka")` za nepostojeći
  username, pogrešnu lozinku i neaktivan nalog; dummy-hash verifikacija na
  nepostojeći username (timing-ublažavanje). Test potvrđuje **doslovno
  identičan** JSON za pogrešnu lozinku i nepoznati username.
- **ADMIN ne prolazi**: `require_role(["RECEPTION"])` radi eksplicitnu
  `current_user.role not in allowed_roles` provjeru — nema "ADMIN uvijek
  prolazi" grane. Testirano za ADMIN na sva tri endpointa (403).
- **Token obrazac**: `secrets.token_urlsafe(32)` sirov token (nikad upisan),
  SHA-256 hash u `sessions.token_hash`, `hmac.compare_digest` u validaciji,
  `expires_at` + `revoked_at` (eksplicitna invalidacija, ne brisanje).
- **Cookie**: `HttpOnly` + `Secure` + `SameSite=Strict` (potvrđeno testom na
  `set-cookie` header).
- **Rate limit**: `@limiter.limit("5/minute")` na login, odvojen od
  `10/minute` na booking-request (potvrđeno testom da trošenje login kvote ne
  utiče na booking-request).
- **F1 (Codex REJECT) zatvoren**: `change_password` sada radi `password_hash`
  izmjenu i `_revoke_active_sessions` u JEDNOJ `with session_factory() as
  session:` sa JEDNIM `session.commit()` — atomski. `_revoke_active_sessions`
  ne commit-uje (pozivalac kontroliše granicu). Adversarni test
  `test_promjena_lozinke_je_atomska_sa_opozivom_sesija` monkeypatch-uje
  `_revoke_active_sessions` da baci `RuntimeError` i potvrđuje rollback
  cijele transakcije (stara lozinka i stara sesija i dalje važeće).
- **Audit granica**: samo `logging.getLogger("dentaland.auth")` (username +
  ishod, `%r` sprečava newline injection) — NIJE napravljena DB audit tabela
  (ide u DENT-IMPROVE-014). Nema nove audit tabele u migraciji.

## Potvrda Codex round2 napomene (ne dupliram kao novi nalaz)

Codex-ova napomena o potencijalnoj konkurentnoj trci (login i
`create_session` su dva odvojena servisna koraka/transakcije; budući
password-change endpoint bi mogao imati usku trku) je validna, ali NIJE
blokirajuća za trenutni scope — nema password-change endpointa niti drugog
konkurentnog pozivaoca `change_password`. Kad se uvede mrežni password-change
tok, ovo ide u zaseban security invariant pregled. Potvrđujem, ne ponavljam.

## CILJ / URAĐENO / NE DIRATI / SLJEDEĆE

```text
CILJ: Argon2id auth + server-side sesije + RECEPTION-only RBAC na 3 staff endpointa, bez OAuth/2FA/audit tabele.
URAĐENO: PASS_WITH_NOTES — scope/acceptance/architecture/security čisti; Codex F1 zatvoren; jedan non-blocking N1 (test_backend/test_models van allowed_paths, nužna posledica).
NE DIRATI: OAuth/SSO/2FA; signup UI; audit DB tabelu (014); ADMIN bypass; klijente (desktop/web); postojeće servise i migracije.
SLJEDEĆE: Radovan human approval (uz svijest o N1). HTTPS ostaje DENT-IMPROVE-015 deployment gate. Budući password-change endpoint zahtijeva ponovni pregled session-issuance trke.
```
