---
task_id: DENT-IMPROVE-014B
reviewer: codex
review_type: independent_code_review
verdict: PASS
scope: PASS
acceptance: PASS
blocking_findings: []
reviewed_commit: ed1bffd2006c8448cdd766e13256f526af3746be
rereviewed_commit: dfcae0dc4bb308dc9546e5dec1177c2507ec41c6
reviewed_at: 2026-08-28
---

# DENT-IMPROVE-014B — Codex review

## CILJ

Nezavisno provjeriti instrumentaciju `LOGIN_SUCCESS`/`LOGIN_FAILURE`
događaja, očuvanje user-enumeration zaštite, minimizaciju audit metadata,
`source_ip` propagaciju i scope taska.

## URAĐENO

Verdikt je **PASS**. Nisam pronašao blocking nalaz.

- Oba neuspješna izlaza iz `authenticate_user` — nepoznat/neaktivan
  korisnik i pogrešna lozinka — upisuju `LOGIN_FAILURE` sa
  `actor_user_id=None`, `source_ip` i isključivo
  `metadata={"username": username}`. Oba vraćaju istu generičku
  `AuthenticationError`; postojeći dummy Argon2 verify na nepoznatom
  korisniku ostao je prisutan. Audit upis je istog oblika na obje grane.
- Pokušani username u internoj append-only audit tabeli ne uvodi javni
  user-enumeration kanal: tabela nije izložena response-u, a HTTP status i
  tijelo ostaju identični. Odluka je proporcionalna incidentnom/brute-force
  istraživanju. Poznat rubni rizik ostaje ako korisnik greškom unese lozinku
  u *username* polje; isti sadržaj se već zapisivao u postojeći
  `logger.info`, pa ga ovaj task nije prvi uveo.
- Lozinka se ne prosljeđuje `write_audit_event` ni na jednom izlazu.
  Uspjeh nema metadata, a neuspjeh sadrži samo username. Pregled koda i
  regresioni testovi potvrđuju da password/token/cookie vrijednosti ne ulaze
  u `metadata_minimal`.
- `backend.main.login` koristi
  `request.client.host if request.client is not None else None`. Nezavisna
  in-process proba sa stvarnim Starlette `Request` čiji je `client=None`
  prošla je i potvrdila da se `source_ip=None` prosljeđuje bez izuzetka.
- `write_audit_event` je ispravno pozvan bez `session=`. Login nema
  okolnu domensku transakciju sa kojom audit treba biti atomski vezan;
  samostalni mod jezgra otvara i commit-uje vlastitu sesiju.
- Sva tri postojeća `logger.info` poziva ostala su na istim granama i sa
  istim porukama; audit pozivi su dodani pored njih.
- Scope od merge-base-a do `ed1bffd` obuhvata samo dozvoljene produkcijske
  i test fajlove (`auth.py`, login dio `backend/main.py`, `test_auth.py`) te
  task dokumentaciju. `models.py`, `audit.py`, `appointments.py`,
  `desktop/**`, `web/**` i `migrations/**` nisu dirani.

## ADVERSARNA I TEST PROVJERA

- `pytest tests/test_auth.py -q` → **28 passed**.
- Direktan poziv stvarnog dekorisanog login handlera sa
  `Request(client=None)` → **PASS**, uhvaćen `source_ip=None`.
- `pytest tests/ -q` → **416 passed, 2 skipped**.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`
  → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 54
  source files**.
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.

## NE DIRATI

- Ne uklanjati postojeći operativni `logger.info` trag; kontrakt traži da
  logging i trajni audit postoje paralelno.
- Ne prebacivati login audit na `session=` obrazac iz appointment toka:
  ovdje nema zajedničke poslovne transakcije.
- Ne izlagati `metadata_minimal` ili pokušani username javnom login
  response-u.

## SLJEDEĆE

Spremno za nezavisni Reviewer 2 review i zatim Radovanov human approval.

## Kratki re-review — prazna `LOGIN_FAILURE` metadata

**Verdikt: PASS.** Blocking nalaza nema.

- Delta `ed1bffd..dfcae0d` je ograničena na `auth.py`, odgovarajući auth
  test i implementerov izvještaj. Na oba `LOGIN_FAILURE` izlaza uklonjen
  je isključivo `metadata={"username": username}`; audit metadata zato
  ostaje na default vrijednosti `None`.
- Preimenovani test ide kroz stvaran pogrešna-lozinka login, pronalazi
  tačno jedan `LOGIN_FAILURE` red i strogo zahtijeva
  `metadata_minimal is None`. Sa prethodnim JSON metadata zapisom taj
  assert ne može lažno proći. Ciljano su prošla i oba failure scenarija.
- Svježa verifikacija na `dfcae0d`: ciljana tri testa **3 passed**;
  kompletan suite **416 passed, 2 skipped**; ruff **All checks passed**;
  mypy **no issues found in 54 source files**; agent sensors **0 blocking
  findings**.

Zaključak prethodnog review-a ostaje **PASS**, sada uz strožu minimizaciju
trajnog audit sadržaja.
