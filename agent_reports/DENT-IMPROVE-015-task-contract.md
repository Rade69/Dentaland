---
task_id: DENT-IMPROVE-015
risk: LOW
implementer: pi
reviewers: [claude]
status: "IMPLEMENTED — izmjene spremne u worktree task/DENT-IMPROVE-015-backend-rate-limit, NIJE commitovano, čeka review + human approval + merge."
created_at: 2026-08-26
---

# DENT-IMPROVE-015 — Rate limiting na preostala 4 backend endpointa

## Kontekst

`CLAUDE.md` non-negotiable pravilo: "Rate limiting na svakom javnom API
endpointu." `backend/main.py` ima 6 endpointa, a `@limiter.limit` imaju samo 2
(`POST /api/auth/login` 5/minute, `POST /api/booking-requests` 10/minute).
Preostala 4 nemaju rate limit — postojeće kršenje pravila, ne opciona
optimizacija.

## Cilj

Dodati `@limiter.limit(...)` na:

| Endpoint | Limit |
|---|---|
| `POST /api/auth/logout` | `10/minute` |
| `GET /api/booking-requests` | `30/minute` |
| `POST /api/booking-requests/{id}/confirm` | `20/minute` |
| `POST /api/booking-requests/{id}/reject` | `20/minute` |

slowapi `@limiter.limit` zahtijeva `request: Request` parametar na funkciji —
`logout` ga već ima, `get_pending_requests`/`confirm`/`reject` ga NEMAJU, pa
se dodaje. Dodati po jedan rate-limit test po endpointu po postojećem obrascu
(`test_rate_limit_na_submit_endpointu`).

## Acceptance

- [ ] svih 6 endpointa u `backend/main.py` ima `@limiter.limit`;
- [ ] `get_pending_requests`/`confirm`/`reject` imaju `request: Request`
      parametar (slowapi zahtjev);
- [ ] 4 nova testa prolaze (`logout` 11→429, `get_pending` 31→429,
      `confirm` 21→429, `reject` 21→429);
- [ ] postojeći backend/auth testovi prolaze bez izmjene ponašanja;
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti.

## Allowed paths

```text
backend/main.py
tests/test_auth.py
tests/test_backend.py
agent_reports/**
```

## Forbidden paths

```text
src/dentaland/**
desktop/**
models.py
migrations/**
web/**
```

**Risk: LOW** — jedan produkcijski fajl, dekoratori + parametar potpisa, bez
šeme/podataka/constraint-a. Ne dodaje novi endpoint, samo pojačava postojeće.

## Otvorena ljudska odluka (NE blokira review, ali MORA prije merge-a)

**Brojevi limita (10/30/20/20) su neizmjerene procjene** za jednu recepciju —
nije mjeren stvaran obrazac korištenja. Radovan treba potvrditi brojeve ili
odobriti kao dovoljno visoke. Ako recepcija normalno prelazi te kvote,
granice treba podići (ili staviti `storage` koji ne odbacuje normalan rad).

## Review

Claude (1 reviewer — LOW po skali). Provjeriti posebno: (a) redoslijed
dekoratora `@app.X` pa `@limiter.limit` (ispod), (b) `request: Request` je
dodat gdje je nedostajao, (c) testovi stvarno pogađaju `429` (a ne lažan
PASS kroz neki drugi status).

## Koordinacija

Nema zavisnosti — bazirano na `main` (`1cd4324`). Ne dira fajlove nijednog
drugog aktivnog taska.
