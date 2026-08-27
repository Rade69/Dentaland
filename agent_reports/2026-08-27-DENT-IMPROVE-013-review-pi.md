---
task_id: DENT-IMPROVE-013
risk: HIGH
reviewer: pi
role: Reviewer 2 (arhitektura/scope + nezavisna reprodukcija)
verdict: PASS_WITH_NOTES
date: 2026-08-27
---

# DENT-IMPROVE-013 — Pi nezavisan review (auth/RBAC)

Nezavisan pregled, izveden od nule — nisam čitao Codex rezonovanje prije
sopstvene provjere (presedan iz REF-03: fresh reviewer). Svi ključni
nalazi su **reprodukovani uživo**, ne preuzeti iz izvještaja.

## Obim / scope — PROLAZI

- **Nema scope creep-a.** Izmjene ograničene na `allowed_paths` (+ `ci.yml`,
  ali identično već-odobrenom `main` commitu `0c038d8` — potvrđeno
  `git diff 0c038d8 -- .github/workflows/ci.yml` je prazan; dodaje samo
  `psycopg2-binary`/`argon2-cffi` u CI instalacionu listu, mehanička
  izmjena, ne novi kod za ocjenu).
- **`desktop/**` i `web/**` STVARNO netaknuti** — nisu u `git status`
  izmjenama, potvrđeno.
- **Nema nove DB audit tabele** — login ide u `logging`, ništa nije
  dodato u šemu koje bi kršilo granicu prema DENT-IMPROVE-014.

## Forbidden paths — PROLAZI

`git diff HEAD` za svih 6 ~~forbidden~~ zaštitnih putanja → **prazan**:

- `src/dentaland/services/availability.py`, `booking.py`, `requests.py` —
  netaknuti (auth je wrapper na routeru, ne dira poslovnu logiku)
- `desktop/**`, `web/**` — netaknuti
- `migrations/env.py`, `alembic.ini` — netaknuti
- `scripts/migrate_sqlite_to_postgres.py` — netaknut
- Postojeće `migrations/versions/*.py` — samo nova `e5f6a7b8c9d0` dodana,
  postojeće netaknute

## Arhitektonska ocjena `src/dentaland/services/auth.py` — PROLAZI

- **Poslovna logika stvarno ostaje u servisnom sloju** — `backend/main.py`
  samo defiše `get_current_user`/`require_role` (FastAPI saves ponasanja) i poziva
  `authenticate_user`/`create_session`/`validate_session`/`invalidate_session`
  iz `dentaland.services.auth`. Nema poslovne/DB logike u routeru.
- **DI obrazac ispoštovan** — `CurrentUserDep = Annotated[AuthenticatedUser,
  Depends(get_current_user)]` i `RequireReceptionDep = Annotated[...,
  Depends(require_role(["RECEPTION"]))]` prate tačno isti
  `Annotated[Type, Depends(...)]` obrazac kao `SessionFactoryDep`. Konzistentno.
- **Token sigurnosni obrazac ispravan** — `secrets.token_urlsafe(32)`, SHA-256
  hash u bazi (nikad sirovi token), `hmac.compare_digest()` za poređenje,
  `expires_at` + `revoked_at` (ne brisanje). Prati postojeći `CLAUDE.md`
  obrazac za cancel-link tokene.
- **Dummy-hash na nepostojeći username** — dobra praksa, ublažava
  timing-based user enumeration (bez testa, ali kod je očigledan).

## CSRF / cookie odluka — TAČNA (nezavisno potvrđeno)

Grep kroz `desktop/**` i `web/**` — **nema browser-based staff klijenta**:

- `desktop/` → nema `httpx`/`requests`/`QNetworkAccessManager`/`urlopen` —
  **nijedan pogodak**
- `web/` → `web/app.js:211` zove SAMO `POST /api/booking-requests` (javni
  submit, ne staff); `web/tests/e2e` testovi zovu samo isti javni endpoint.
  **Nijedan** poziv na `GET /api/booking-requests`/`confirm`/`reject`.

Zato `SameSite=Strict` bez punog CSRF token mehanizma je **stvarno
dovoljno za sada** — ne postoji cross-origin vektor. Obrazloženje u planu
je realno, ne prazna pretpostavka. Ovo ostaje validno sve dok se ne doda
admin web panel (tada CSRF token postaje obavezan).

## Codex F1 fix — NEZAVISNO REPRODUKOVAN

Nisam prihvatio na riječ — **dokazao sam da test stvarno hvata bug**:

1. Napravio sam backup `auth.py`.
2. Privremeno vratio stari **dvotransakcijski** obrazac (zaseban commit
   hash-a, pa zaseban opoziv sesija) — kod kojim je `change_password`
   upisivao novu lozinku u jednoj transakciji, a opoziv sesija u drugoj.
3. **F1 test PADA** sa tim starim kodom (`test_promjena_lozinke_je_atomska_sa_opozivom_sesija`),
   i **PROLAZI** sa fixom.
4. Vratio original (potvrđeno `diff` da je identičan).

Dakle atomska `change_password` (jedna sesija, jedan `commit`, rollback
cijele transakcije na bilo koji izuzetak) je stvarno ispravna, ne samo
"prolazi test". F1 koji je Codex našao je pravilno riješen.

## Standardni gateovi (reprodukovano)

- `pytest tests/ -q` → **395 passed, 2 skipped** (potvrđeno, ne preuzeto)
- `ruff check src/dentaland desktop backend tests scripts/create_user.py scripts/agent_sensors.py` → **All checks passed**
- `mypy src/dentaland desktop backend` → **53 fajla, 0 grešaka**
- `python scripts/agent_sensors.py --all` → **0 blocking findings**

## Nalazi

- **N1 (non-blocking, kozmetički):** **Nema automatizovanog testa koji
  provjerava da je lozinka u bazi Argon2id hash.** Acceptance kriterijum
  "lozinke su Argon2id hash, nikad plaintext" je pokriven **implicitno**
  (kod koristi `argon2-cffi` `PasswordHasher` i `test_login_*` koriste
  `hash_password`), ali ne postoji eksplicitni test da hash počinje sa
  `$argon2id$`. Implementerov izvještaj kaže "`$argon2id$` prefiks
  provjeren ručno" — to je tačno, ali je ručna, ne trajna zaštita.
  **Potvrdio sam lično** da `hash_password("...")` stvarno vraća
  `$argon2id$v=19$...` — tako da je zaštita stvarno na mjestu, samo
  nedostaje regresioni test. Preporuka: dodati mali test na prefiks (npr.
  `assert hash_password("x").startswith("$argon2id$")`).
- **R1 (napomena, ne blokira):** `test_models.py::test_sve_tabele_su_kreirane`
  proširen sa `users`/`sessions` — nužna posljedica, obrazložena u planu.
  Nije proširenje obima, ispravno.

## Verdict: PASS_WITH_NOTES

Kod je arhitektonski čist, obim strogo ispoštovan, svi forbidden paths
netaknuti, CSRF/cookie odluka realno tačna (nezavisno potvrđena grep-om),
Codex-ov F1 atomski fix dokazano ispravan (ponovio sam fail⇒pass ciklus),
Argon2id stvarno korišten. Nema blokirajućih nalaza.

Jedini nalaz (N1) je nedostatak eksplicitnog testa za Argon2id prefiks —
ne blokira merge, ali vrijedi kao trivijalan follow-up da acceptance
"nikad plaintext" postane trajno, testom zaštićen.
