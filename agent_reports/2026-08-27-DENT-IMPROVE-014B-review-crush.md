---
task_id: DENT-IMPROVE-014B
risk: HIGH
reviewer: crush
role: Reviewer 2 (arhitektura/konzistentnost, nezavisna perspektiva)
verdict: PASS
date: 2026-08-28
---

# DENT-IMPROVE-014B — Crush nezavisan review (audit LOGIN_SUCCESS/LOGIN_FAILURE)

## Re-review (28.8.2026) — N1 riješen, verdikt podignut na PASS

Commit `dfcae0d` ("fix(auth): LOGIN_FAILURE audit metadata prazna, ne sadrzi
pokusani username") primijenjuje moj N1 nalaz (opcija b — prazna
`LOGIN_FAILURE` metadata). Provjerio sam diff `ed1bffd..dfcae0d` — minimalan
i tačno ono što je traženo, ništa više:

- `auth.py`: uklonjen `metadata={"username": username}` sa OBA `LOGIN_FAILURE`
  poziva (nepostojeći username i pogrešna lozinka); `LOGIN_FAILURE` sada
  upisuje `metadata=None` (default). Docstring dopunjen Radovanovom odlukom.
- `test_auth.py`: test preimenovan u
  `test_login_failure_metadata_je_prazna_ne_sadrzi_ni_username_ni_lozinku`;
  asercija je sada `assert failure_events[0].metadata_minimal is None` —
  **genuino** hvata prazninu (ako bi se username vratio, `metadata_minimal`
  bi bio JSON string, ne `None`, pa bi test pao).

Verifikacija na `dfcae0d` (privremeni worktree): `pytest tests/ -q` →
**416 passed, 2 skipped**; `pytest tests/test_auth.py -q` → **28 passed**;
`ruff`/`mypy` (54 fajla)/`agent_sensors.py --all` → svi čisti. N1 više nije
aktivan, nema novih nalaza.

```yaml
verdict: PASS
blocking_findings: []
```

---

Nezavisan pregled od nule nad `task/DENT-IMPROVE-014B-audit-login` (commit
`ed1bffd`, checkout-ovan u privremeni worktree radi čistih verifikacija).
Codex radi paralelno kao Reviewer 1 (test-kvalitet/adversarni fokus) — ovaj
review je druga, arhitektonska perspektiva i namjerno NE duplira test-analizu.

## Verdikt

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## Fokus 1 — arhitektonska čistoća (framework-agnostičan servisni sloj)

**PROLAZI.** `src/dentaland/services/auth.py` NE uvozi ništa FastAPI/Starlette
specifično — samo `dentaland.models` (`AuditAction`, `User`, `UserRole`,
`utcnow`) i `dentaland.services.audit` (`write_audit_event`). `source_ip`
ulazi kao običan `str | None` keyword-only parametar (default `None`), ne kao
`Request`/`Request`-izveden tip. `request.client.host` se ekstrahuje JEDINO u
`backend/main.py` login route handleru (`request.client is not None` guard,
`NULL` inače) i prosljeđuje kao čist string — granica framework→servisni sloj
je ispravno postavljena.

## Fokus 2 — konzistentnost sa DENT-IMPROVE-014C obrascem

**PROLAZI — razlika je opravdana, ne nedosljednost.** Oba poziva koriste isti
`write_audit_event(session_factory, action, ...)` API, ali:

- `014C` (appointments) prosljeđuje `session=session` — audit red ide u ISTU
  transakciju kao izmjena termina (atomičnost: ili oboje ili ništa).
- `014B` (login) NE prosljeđuje `session=` — login nema okolnu transakciju;
  `write_audit_event` tada otvara i commit-uje sopstvenu sesiju (samostalni
  mod).

Ova dva moda su eksplicitno deo dizajna `write_audit_event` (dokumentovano u
docstringu `src/dentaland/services/audit.py` linije 23-36 i 99-123: "session
vs session_factory"). `014B` koristi tačno onaj mod koji je za njega
predviđen — nema kršenja API ugovora.

## Fokus 3 — nazadna kompatibilnost (`source_ip`)

**PROLAZI.** `authenticate_user(session_factory, username, password, *,
source_ip: str | None = None)` — `source_ip` je keyword-only sa default
`None`. Provjerio sam SVE pozivaoce u produkcijskom kodu na grani:

- `backend/main.py:226` — `authenticate_user(..., source_ip=source_ip)` (novo).
- `tests/test_auth.py:379, 382, 539` — pozivaju sa 3 poziciona arg (bez
  `source_ip`), i dalje rade (default `None` → audit red sa `source_ip=NULL`).

Nema desktop pozivaoca `authenticate_user` (desktop ne zove backend/auth
sloj — potvrđeno ranije u DENT-IMPROVE-013). Novi test
`test_authenticate_user_bez_source_ip_upisuje_audit_sa_null_ip` eksplicitno
pokriva ovu kompatibilnost.

## Nalaz

### N1 (non-blocking) — `LOGIN_FAILURE` metadata sadrži pokušani username u TRAJNOJ append-only tabeli

- Implementer je (svjesno, po kontraktu) stavio `metadata={"username":
  username}` za `LOGIN_FAILURE`. Task Contract tačka 3 eksplicitno dozvoljava
  obe opcije ("username ili prazno"), i odluka je dokumentovana. Ne sporeći
  validnost odluke, treba istaći jednu nijansu koju implementerov "nasleđen
  rubni slučaj" argument ne naglašava dovoljno:
- **Trajnost je kvalitativno drugačija od loga.** `logger.info("LOGIN_FAILURE
  username=%r", ...)` (DENT-IMPROVE-013) piše u ROTIRAJUĆI operativni log;
  `audit_events.metadata_minimal` je APPEND-ONLY compliance-grade zapis koji
  se NIKAD ne briše. U rubnom slučaju "korisnik greškom ukuca lozinku u polje
  za username", ta lozinka bi trajno ostala u `metadata_minimal` — strože od
  rotirajućeg loga, i nije čisto "nasleđen" rizik (trajnost je nova).
- Rizik je nizak (zahtijeva da korisnik ukuca lozinku u username polje) i
  NE blokira — kontrakt dozvoljava obe opcije, odluka je svjesna, i `source_ip`
  /enumeration zaštita (`actor_user_id=NULL`) nisu pogođeni. Ali ovo treba
  biti eksplicitno vidljivo Radovanu pri human approval-u: ili (a) prihvatiti
  svjesno, ili (b) preći na strožu varijantu (prazan `metadata` za
  `LOGIN_FAILURE`).

## Potvrđeno lično (ne iz izvještaja)

Verifikacije pokrenute u privremenom worktree-u na `ed1bffd`.

| Provjera | Rezultat |
|---|---|
| `src/dentaland/services/audit.py` (jezgro) prisutan | DA (6297 B) |
| `git diff main...014B` (kod) | samo `backend/main.py`, `auth.py`, `test_auth.py` + `agent_reports/**` |
| forbidden paths (`models.py`, `audit.py`, `appointments.py`, `desktop/**`, `web/**`, `migrations/**`) | **netaknuti** (nijedan u diff-u) |
| `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py` | **All checks passed** |
| `mypy src/dentaland desktop backend` | **Success: no issues found in 54 source files** |
| `python scripts/agent_sensors.py --all` | **0 blocking findings** |
| `pytest tests/ -q` | **416 passed, 2 skipped** (12 warnings) |
| `pytest tests/test_auth.py -q` | **28 passed** (22 postojeća + 6 nova audit testa) |

## Potvrđeno čitanjem koda

- `LOGIN_SUCCESS`: `actor_user_id=user.id`, `resource_type="user"`,
  `resource_id=user.id`, `source_ip` — tačno.
- `LOGIN_FAILURE` (oba slučaja — nepostojeći username i pogrešna lozinka):
  `actor_user_id=None`, `source_ip`, `metadata={"username": username}` —
  tačno, `NULL` actor čuva enumeration-zaštitu i na audit nivou.
- `write_audit_event` pozvan PORED `logger.info` (logging nije brisan) —
  tačno po kontraktu ("dodaj pored, ne zamjenjuj").
- Lozinka se NIGDJE ne pojavljuje u `metadata_minimal` (potvrđeno spot-check
  testovima + čitanjem koda: `metadata` sadrži samo `username`, nikad
  `password`).
- `CHANGE_ROLE` ostaje dormant — nema novog koda oko nje.

## CILJ / URAĐENO / NE DIRATI / SLJEDEĆE

```text
CILJ: LOGIN_SUCCESS/LOGIN_FAILURE audit zapisi (append-only) uz source_ip iz stvarnog Request, bez mijenjanja jezgra/klijenata.
URAĐENO: PASS_WITH_NOTES — arhitektonski čisto (framework-agnostičan servisni sloj), konzistentno sa 014C (session vs session_factory), nazadno kompatibilno; jedan non-blocking N1 (username u trajnom metadata).
NE DIRATI: audit jezgro, models, appointments (014C), desktop/web, migracije, logging (dodaje se pored).
SLJEDEĆE: Radovan human approval — svjesna odluka o N1 (username u LOGIN_FAILURE metadata vs stroža prazna varijanta). Uskladiti sa Codex (Reviewer 1) zaključkom.
```
