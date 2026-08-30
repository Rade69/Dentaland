---
task_id: DENT-IMPROVE-019
reviewer: codex
reviewed_commit: b588ac0
verdict: REJECT
scope: PASS
acceptance: FAIL
blocking_findings:
  - F2: Grana sadrži još uvijek odbijenu DENT-IMPROVE-018 implementaciju
reviewed_at: 2026-08-30
---

# DENT-IMPROVE-019 — Codex review

## Verdikt

REJECT. Postgres testovi prolaze (4 passed), ali migracija ne pokriva sve TZDateTime kolone nakon spajanja paralelnih grana.

## F1 — HIGH

Nedostaju appointments.telegram_link_token_expires_at i appointments.telegram_subscribed_at. DENT-IMPROVE-018 migracija ih kreira kao sa.DateTime() bez timezone=True. Zato ih ni jedan merge redoslijed ne pretvara pouzdano u timestamptz: ako 019 ide prvi, 018 ih kasnije doda pogrešnog tipa; ako 018 ide prvi, 019 ih ne alteruje.

Linearizovati migration chain 018→019, dodati obje kolone u ispravku (ili ih u 018 odmah kreirati sa timezone=True) i inspector test proširiti na svih 16 vremenskih kolona. USING AT TIME ZONE UTC pretpostavka je prihvatljiva jer nema stvarnih produkcijskih Postgres podataka.

## Handoff

CILJ: sve vremenske kolone postaju timestamptz.
URAĐENO: REJECT — 14 kolona pokriveno, 2 Telegram kolone nisu.
NE DIRATI: round-trip logiku i UTC pretpostavku.
SLJEDEĆE: uskladiti 018/019 migracioni lanac i ponoviti review.

## Ponovni pregled — 2026-08-30

Grana je i dalje na istom pregledanom commitu `98b159278`; nema novog fixa
iznad prethodnog review-a. Migracija zato i dalje izostavlja dvije Telegram
datetime kolone i verdikt ostaje **REJECT**.

## Re-review — commit `b588ac0`

Prethodni F1 je **zatvoren**. Lanac je linearizovan kao
`f6a7b8c9d0e1 -> a7b8c9d0e1f2 -> g7h8i9j0k1l2`, `alembic heads` vraća
tačno jedan head, obje Telegram datetime kolone su dodane u eksplicitnu
listu, a inspector test sada provjerava svih 16 kolona. Svježi run protiv
stvarnog PostgreSQL-a iz lokalne `.env` konfiguracije: **4 passed**.
`ruff` za izmijenjenu migraciju/test je čist.

Verdikt grane ipak ostaje **REJECT** zbog F2/HIGH: commit `fd5a957` je u ovu
granu mergovao cijeli DENT-IMPROVE-018, koji je još na `1dacf765` i još ima
tri otvorena HIGH nalaza iz zasebnog review-a. Merge 019 prije popravljenog i
odobrenog 018 bi zato u `main` unio poznate webhook/token sigurnosne greške.
019 je spreman tek kada se F1-F3 na 018 zatvore i taj popravljeni 018 postane
njegov stvarni ancestor (merge/rebase), nakon čega treba ponoviti integracioni
gate.
