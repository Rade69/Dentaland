---
task_id: DENT-IMPROVE-014B
implementer: claude
status: "IMPLEMENTED — Codex (PASS) i Crush (PASS_WITH_NOTES, N1) review završeni. N1 fix primijenjen (28.8.2026). Čeka kratak re-review pa human approval."
---

## Fix nakon review N1 (Crush, 28.8.2026) — prazna LOGIN_FAILURE metadata

Crushov N1 (non-blocking): audit tabela je append-only (nikad se ne
briše), za razliku od rotirajućeg `logger.info` traga — ako korisnik
greškom ukuca lozinku u polje za username, ona bi TRAJNO ostala u
`metadata_minimal`. Radovan je, nakon obrazloženja tradeoffa, odlučio da
je trajnost veći rizik od gubitka istražne vrijednosti (mali broj naloga
u sistemu čini "koji username je bio meta" niskovrijednim podatkom).

**Izmjena:** `metadata={"username": username}` uklonjeno sa oba
`LOGIN_FAILURE` poziva u `src/dentaland/services/auth.py` — `metadata`
sad ostaje na default `None`. Docstring modula ažuriran. Test
`test_login_failure_metadata_sadrzi_pokusani_username_ali_nikad_lozinku`
preimenovan u `test_login_failure_metadata_je_prazna_ne_sadrzi_ni_username_ni_lozinku`,
sad provjerava `metadata_minimal is None` umjesto prisustva username-a.
Sekcija "Odluka: LOGIN_FAILURE metadata_minimal sadrži pokušani
username" niže u ovom izvještaju opisuje ORIGINALNU (sad promijenjenu)
odluku — ostavljena kao istorijski kontekst, ne kao trenutno stanje.

## Ispravka atribucije (27.8.2026)

Task Contract je izvorno naveo "implementer: pi", pretpostavljajući da će
stvaran Pi alat (koji Radovan ručno pokreće u odvojenom prozoru) uraditi
implementaciju — isti obrazac koji se koristio za review u cijeloj ovoj
seriji taskova. Umjesto toga je Claude session pokrenuo sopstveni
pod-agent i sam implementirao kod, greškom ga označivši kao "implementer:
pi". Radovan je primijetio nesklad i tražio ispravku. Kod je nezavisno
verifikovan (od strane Claude glavne sesije, van pod-agenta) i zadržan —
Radovanova odluka je da se ispravi ATRIBUCIJA (implementer: claude), ne
da se kod odbaci i ponovo piše. Codex + Crush review i dalje daju
nezavisnu drugu/treću perspektivu (nijedan nije pisao ovaj kod).

# DENT-IMPROVE-014B — Audit: LOGIN_SUCCESS/LOGIN_FAILURE

Plan prije koda: `agent_reports/2026-08-27-DENT-IMPROVE-014B-plan.md`.

## Šta je urađeno

- `src/dentaland/services/auth.py`: `authenticate_user` dobija opcioni
  keyword-only `source_ip: str | None = None` (default ne mijenja
  postojeće pozivaoce). Na sva tri postojeća izlaza iz funkcije (nepostojeći/
  neaktivan korisnik, pogrešna lozinka, uspjeh) dodat je
  `write_audit_event(...)` poziv POREDO sa postojećim `logger.info(...)` —
  logging nije brisan/mijenjan.
  - `LOGIN_FAILURE`: `actor_user_id=None`, `metadata={"username": username}`.
  - `LOGIN_SUCCESS`: `actor_user_id=user.id`, `resource_type="user"`,
    `resource_id=user.id`.
  - `write_audit_event` pozvan u samostalnom modu (bez `session=`) — login
    audit nema okolnu transakciju, tačno kako kontrakt traži.
- `backend/main.py`: `login()` route handler izvlači
  `source_ip = request.client.host if request.client is not None else None`
  i prosljeđuje ga u `authenticate_user(...)`. Jedina izmjena u ovom
  fajlu — logout i ostali endpointi netaknuti.
- `tests/test_auth.py`: 6 novih testova (`test_login_uspjeh_upisuje_login_success_audit_zapis`,
  `test_login_pogresna_lozinka_upisuje_login_failure_sa_null_actor`,
  `test_login_nepostojeci_username_upisuje_login_failure_sa_null_actor`,
  `test_login_failure_metadata_sadrzi_pokusani_username_ali_nikad_lozinku`,
  `test_login_metadata_minimal_nikad_ne_sadrzi_lozinku_ni_na_uspjeh`,
  `test_authenticate_user_bez_source_ip_upisuje_audit_sa_null_ip`).

## Odluka: `LOGIN_FAILURE` `metadata_minimal` sadrži pokušani username

Uključen je pokušani `username` u `metadata_minimal` za `LOGIN_FAILURE`.
Razlog: `actor_user_id=NULL` je već primarna user-enumeration zaštita na
audit nivou (audit tabela nije javno izložena, pa dodatni username tu ne
otvara enumeration kanal prema napadaču); podatak je koristan za istragu
brute-force obrazaca; i identičan podatak (`username`) se već bilježi na
istom mjestu preko `logger.info(...)` od DENT-IMPROVE-013 — ovo ga samo
duplira u trajniju tabelu, ne uvodi novu vrstu izloženosti. Poznat,
nasljeđen (ne nov) rubni slučaj: korisnik koji greškom otkuca lozinku u
polje za username će tu lozinku ostaviti i u logu i u audit metadata —
isti rizik već postoji od DENT-IMPROVE-013, van scope-a ovog taska za
rješavanje. Puna analiza u planu.

## Acceptance criteria

| Kriterijum | Status |
|---|---|
| `LOGIN_SUCCESS`/`LOGIN_FAILURE` upisuju stvaran red u `audit_events` | DA — testovi |
| `actor_user_id` tačan za uspjeh, `NULL` za neuspjeh | DA — testovi |
| `source_ip` popunjen iz stvarnog HTTP zahtjeva | DA — testovi (TestClient) |
| Lozinka/token se nigdje ne pojavljuju u `metadata_minimal` | DA — spot-check test |
| `pytest`/`ruff`/`mypy`/`agent_sensors.py --all` čisti | DA — vidi ispod |
| `appointments.py`, `desktop/**`, `web/**` netaknuti | DA — `git status` potvrđuje |

## Verifikacija

- `pytest tests/test_auth.py -q` → 28 passed (22 postojeća + 6 nova).
- `pytest tests/ -q` (pun paket) → 416 passed, 2 skipped (isti skip kao
  baseline, nepovezano sa ovim taskom), 0 failed.
- `ruff check src/dentaland/services/auth.py backend/main.py tests/test_auth.py`
  → All checks passed. (Napomena: `ruff check .` na cijelom repou javlja 6
  grešaka u `scripts/coordination.py` — pre-existing, van `allowed_paths`,
  nisu dirane u ovom tasku.)
- `mypy src/dentaland backend` (standardna projektna komanda, vidi ranije
  agent_reports) → Success: no issues found in 19 source files.
- `python scripts/agent_sensors.py --all` → Result: 0 blocking findings.

## Šta NIJE dirano

`src/dentaland/models.py`, `src/dentaland/services/audit.py`,
`src/dentaland/services/appointments.py`, `desktop/**`, `web/**`,
`migrations/**` — potvrđeno `git status --short` (samo `backend/main.py`,
`src/dentaland/services/auth.py`, `tests/test_auth.py` mijenjani +
`agent_reports/**` dodani).

`CHANGE_ROLE` ostaje dormant — nema novog koda oko nje.

## Sažetak

Dodana su dva `write_audit_event` poziva u `authenticate_user`
(`src/dentaland/services/auth.py`) — `LOGIN_SUCCESS` sa tačnim
`actor_user_id`, `LOGIN_FAILURE` sa `actor_user_id=NULL` — pored
postojećeg `logger.info`, bez brisanja logginga. `source_ip` dolazi iz
pravog FastAPI `Request` objekta u `backend/main.py` login handleru, kroz
novi opcioni `source_ip` parametar funkcije (default `None`, stari
pozivaoci nepromijenjeni). `LOGIN_FAILURE` metadata svjesno uključuje
pokušani username (obrazloženje u izvještaju) — nikad lozinku. 6 novih
testova pokriva oba ishoda, `source_ip` popunjavanje, i spot-check da
lozinka nikad nije u `metadata_minimal`. Pun `pytest` (416 passed, 2
pre-existing skips), `ruff`, `mypy`, `agent_sensors.py --all` čisti na
mojim fajlovima. `models.py`, `audit.py`, `appointments.py`, `desktop/**`,
`web/**`, `migrations/**` netaknuti — potvrđeno. Spreman za Codex
(Reviewer 1) + Crush (Reviewer 2) review.
