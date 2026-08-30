---
task_id: DENT-IMPROVE-020
reviewer: codex
reviewed_commit: c7a363f12ddbf0edd25e76e371b172c67dd585ae
verdict: REJECT
scope: PASS
acceptance: FAIL
blocking_findings:
  - F1: 403/429/5xx cure kao sirovi httpx.HTTPStatusError prema GUI sloju
reviewed_at: 2026-08-30
---

# DENT-IMPROVE-020 — Codex review

## Verdikt

REJECT. Scope je čist i ciljani testovi prolaze (35 passed), ali glavni HTTP error contract nije ispunjen.

## F1 — MEDIUM

_request prevodi samo connect/timeout i 401. Metode zatim pozivaju response.raise_for_status, pa 403, 429 i 5xx odgovori izlaze kao sirovi httpx.HTTPStatusError. Nezavisna get_doctors proba sa mock 500 odgovorom dala je upravo httpx.HTTPStatusError. DashboardPanels se eagerno refresha, pa server error može srušiti remote prozor tracebackom.

Centralizovati mapiranje: 401/403 auth/session, 429 rate-limit, 5xx/server i ostali statusi u GUI-prijateljski ApiClientError. Dodati parametrizovane testove za sve metode/status grane i potvrditi da GUI prikazuje poruku umjesto pada.

MainWindow i desktop/app.py nisu dirani; nema hardkodiranog VPS defaulta, a endpointi koriste servisni sloj i RECEPTION RBAC.

## Handoff

CILJ: robustan uzak desktop→API most.
URAĐENO: REJECT — normalni tok radi, error contract ne.
NE DIRATI: odvojeni entry point i lokalnu aplikaciju.
SLJEDEĆE: prevesti sve HTTP greške i ponoviti review.
