---
task_id: DENT-IMPROVE-015
risk: LOW
implementer: pi
reviewers: [claude]
verdict: PENDING_REVIEW
commits: []
created_at: 2026-08-26
---

# DENT-IMPROVE-015 — Rate limiting na preostala 4 backend endpointa

## Task Contract

Vidi `agent_reports/DENT-IMPROVE-015-task-contract.md`.

## Šta je urađeno

1. `backend/main.py`
   - `@limiter.limit("10/minute")` na `POST /api/auth/logout`.
   - `@limiter.limit("30/minute")` na `GET /api/booking-requests`.
   - `@limiter.limit("20/minute")` na `POST /api/booking-requests/{id}/confirm`.
   - `@limiter.limit("20/minute")` na `POST /api/booking-requests/{id}/reject`.
   - Dodat `request: Request` parametar na `get_pending_requests`, `confirm`,
     `reject` (slowapi `@limiter.limit` to zahtijeva; `logout` ga je već imao).
2. `tests/test_auth.py` — `test_rate_limit_na_logout_endpointu` (11→429).
3. `tests/test_backend.py` — `test_rate_limit_na_get_pending_endpointu`
   (31→429), `test_rate_limit_na_confirm_endpointu` (21→429),
   `test_rate_limit_na_reject_endpointu` (21→429).

## Verifikacija (stvarni rezultati, pokrenuto)

| Provjera | Rezultat |
|---|---|
| `pytest tests/test_auth.py tests/test_backend.py -q -k rate_limit` | **7 passed** (2 stara + 1 submit + 4 nova) |
| `pytest tests/test_auth.py tests/test_backend.py tests/test_postgres_migration.py -q` | **41 passed, 2 skipped** |
| `pytest tests/ -q` | **414 passed, 2 skipped** (baseline 410 + 4 nova) |
| `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py` | **All checks passed** |
| `mypy src/dentaland desktop backend` | **Success: no issues found in 54 source files** |

## Review

Čeka Claude (1 reviewer), pa human approval.

## Integration status

`IMPLEMENTED → AWAITING_REVIEW` — nije commitovano, nije mergovano.

## Napomena — ljudska odluka prije merge-a

Brojevi limita (10/30/20/20) su neizmjerene procjene (vidi Task Contract
"Otvorena ljudska odluka"). Implementacija je spremna, ali brojevi traže
Radovanovu potvrdu.

## Odbačene opcije

- **`SlowAPIMiddleware` globalno** — odbačeno; postojeći obrazac je
  per-route `@limiter.limit` (kvota po ruti, ne globalna), zadržan radi
  konzistentnosti i nezavisnih limita po endpointu.
