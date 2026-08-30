---
task_id: DENT-IMPROVE-018
reviewer: codex
reviewed_commit: 1dacf765958668f4764268af38bce0bc99dde88d
verdict: REJECT
scope: PASS
acceptance: FAIL
blocking_findings:
  - F1: Webhook parsira body prije secret provjere
  - F2: Bot token može procuriti kroz logovani httpx izuzetak
  - F3: Potrošnja opt-in tokena nije atomska
reviewed_at: 2026-08-30
---

# DENT-IMPROVE-018 — Codex review

## Verdikt

REJECT. Ciljani testovi prolaze (36 passed), ali postoje tri blocking nalaza.

## F1 — HIGH

Endpoint prima payload kao dict, pa FastAPI parsira JSON prije ulaska u handler i secret provjere. Živa proba sa pogrešnim secretom i neispravnim JSON-om vratila je 422 JSON decode error, ne obavezni 403. Handler mora prvo provjeriti header preko Request objekta, pa tek onda parsirati body.

## F2 — HIGH

send_message stavlja bot token u URL i loguje cijeli httpx exception. HTTPStatusError string dokazano sadrži URL /botSECRET123/sendMessage, pa stvarni token može završiti u logu. Logovati samo sanitizovan status/tip greške.

## F3 — HIGH

consume_telegram_link_token radi SELECT pa Python izmjene i COMMIT. Dva istovremena webhooka mogu oba pročitati chat_id IS NULL i oba prihvatiti isti token. Potreban je atomski conditional UPDATE sa RETURNING (ili zaključavanje) i konkurentni regresioni test.

## Handoff

CILJ: siguran jednokratni Telegram opt-in.
URAĐENO: REJECT — F1–F3 blokiraju acceptance.
NE DIRATI: minimizovani tekst i email wiring.
SLJEDEĆE: popravke pa Codex re-review.

## Ponovni pregled — 2026-08-30

Grana je i dalje na istom pregledanom commitu `1dacf765`; nema novog fixa
iznad prethodnog review-a. Zato sva tri blokirajuća nalaza ostaju otvorena i
verdikt ostaje **REJECT**.
