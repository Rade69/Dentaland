---
task_id: DENT-IMPROVE-014B
risk: HIGH
implementer: claude
reviewers: [codex, crush]
status: "IMPLEMENTED — čeka review (Codex + Crush, v3.1 princip #7). Claude (koordinator) nezavisno potvrdio: 416 pytest, ruff, mypy, agent_sensors čisti."
created_at: 2026-08-27
depends_on: DENT-IMPROVE-014
---

# DENT-IMPROVE-014B — Audit: LOGIN_SUCCESS/LOGIN_FAILURE

## Zavisnost — NE POČINJI dok se ovo ne provjeri

Ovaj task uvozi `AuditEvent`/`write_audit_event` iz
`DENT-IMPROVE-014` (jezgro). **Provjeri prije bilo čega**: da li je
`src/dentaland/services/audit.py` i `AuditEvent` model stvarno u `main`
(`git log --oneline main | grep DENT-IMPROVE-014`, i
`ls src/dentaland/services/audit.py` nakon `git pull`). Ako nije
mergovano, STANI i javi — ne pravi svoju kopiju/duplikat tih fajlova.

## Kontekst

Paralelan par sa `DENT-IMPROVE-014C` (implementer Crush) — nula
preklapanja fajlova (potvrđeno u `DENT-IMPROVE-014` kontraktu prije
starta oba taska). Zajedno ova dva taska instrumentišu sva mjesta gdje se
audit događaji dešavaju; jezgro (model + `write_audit_event`) je već
gotovo.

`src/dentaland/services/auth.py` (`DENT-IMPROVE-013`) trenutno ima:

```python
logger.info("LOGIN_SUCCESS username=%r", username)
...
logger.info("LOGIN_FAILURE username=%r", username)
```

na dva mjesta u `authenticate_user`. Ovaj task DODAJE prave audit zapise
pored postojećeg logovanja (ne zamjenjuje ga — `logging` ostaje kao jeftin
operativni trag, `audit_events` je compliance-grade trajan zapis).

## Cilj

`LOGIN_SUCCESS` (sa pravim `actor_user_id`) i `LOGIN_FAILURE` (sa
`actor_user_id=NULL` — user enumeration zaštita se primjenjuje i na audit
nivou, ne samo na HTTP response) zapisi u `audit_events`, uz `source_ip`
iz stvarnog HTTP zahtjeva.

## Required scope

1. `authenticate_user` (ili poziv iz `backend/main.py` login route
   handlera — implementer bira gdje tačno, dokumentuje zašto) poziva
   `write_audit_event(action=AuditAction.LOGIN_SUCCESS, actor_user_id=user.id, source_ip=...)`
   na uspjeh, `write_audit_event(action=AuditAction.LOGIN_FAILURE, actor_user_id=None, source_ip=...)`
   na neuspjeh.
2. `source_ip` mora doći iz stvarnog FastAPI `Request` objekta
   (`request.client.host`) — dostupan u `backend/main.py` route handleru,
   ne u `auth.py` (koji trenutno nema pristup `Request`). Ako implementer
   bira da doda audit poziv unutar `authenticate_user`, mora proširiti
   njen signature sa opcionim `source_ip: str | None = None` parametrom
   (ne mijenjati postojeće pozivaoce koji ga ne prosljeđuju — default
   `None`).
3. **`LOGIN_FAILURE` `metadata_minimal`**: implementer odlučuje da li
   staviti pokušani `username` (nije tajna, korisno za istragu brute-force
   obrazaca) ili ostaviti prazno (stroža enumeration-zaštita i na audit
   nivou). Dokumentovati odluku i razlog u izvještaju — obje opcije su
   prihvatljive, ali mora biti svjesna odluka, ne slučajno.
4. `CHANGE_ROLE` — **ostaje dormant u ovom tasku** (nema role-change
   funkcionalnosti u kodu, per `DENT-IMPROVE-014` kontrakt). Ne graditi
   je ovdje.
5. Testovi (dopuna `tests/test_auth.py` ili novi `tests/test_audit_auth.py`):
   - Uspješan login upisuje `LOGIN_SUCCESS` sa tačnim `actor_user_id`.
   - Neuspješan login (pogrešna lozinka I nepostojeći username, oba
     scenarija) upisuje `LOGIN_FAILURE` sa `actor_user_id=NULL`.
   - `source_ip` se stvarno popunjava iz test klijenta.
   - Spot-check: lozinka se nikad ne pojavljuje u `metadata_minimal`.

## Šta NE dirati

- `src/dentaland/models.py`, `src/dentaland/services/audit.py` (jezgro iz
  `DENT-IMPROVE-014` — samo POZIVAJ `write_audit_event`, ne mijenjaj je).
- `src/dentaland/services/appointments.py` (`DENT-IMPROVE-014C` posao).
- `desktop/**`, `web/**`.
- Ne graditi CHANGE_ROLE endpoint.
- Postojeće `logger.info(...)` pozive u `auth.py` NE brisati — dodaj
  audit poziv POREDO, ne zamjenjuj.

## Acceptance criteria

- [ ] `LOGIN_SUCCESS`/`LOGIN_FAILURE` upisuju stvaran red u `audit_events`
- [ ] `actor_user_id` tačan za uspjeh, `NULL` za neuspjeh
- [ ] `source_ip` popunjen iz stvarnog HTTP zahtjeva
- [ ] Lozinka/token se nigdje ne pojavljuju u `metadata_minimal`
- [ ] Postojeći `pytest tests/ -q` (uključujući sav `DENT-IMPROVE-013`
      auth suite), `ruff`, `mypy`, `agent_sensors.py --all` ostaju čisti
- [ ] `appointments.py`, `desktop/**`, `web/**` netaknuti

## Allowed paths

```text
src/dentaland/services/auth.py
backend/main.py                          (SAMO login/logout route handleri)
tests/test_auth.py                       (ili novi tests/test_audit_auth.py)
agent_reports/**
```

## Forbidden paths

```text
src/dentaland/models.py
src/dentaland/services/audit.py
src/dentaland/services/appointments.py
desktop/**
web/**
migrations/**
```

## Review

Codex (Reviewer 1, obavezan, v3.1 princip #7) + Crush (Reviewer 2, pošto
je Pi implementer — nezavisna sesija/agent).

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-014B --agent pi --paths src/dentaland/services/auth.py,backend/main.py
```

Paralelno sa `DENT-IMPROVE-014C` (Crush) — provjeri `coordination.py
status` prije starta da potvrdiš da nema konflikta.
