---
task_id: DENT-013
risk: LOW
implementer: codex
reviewers: [pending]
verdict: PENDING_REVIEW
commits: []
created_at: 2026-08-17T12:00:00+02:00
---

# DENT-013 — Obavještenje o obradi ličnih podataka

## Task Contract

Vidi `agent_reports/DENT-013-task-contract.md`.

## Šta je urađeno

- Dodana je zasebna `web/privacy.html` stranica sa 12 odjeljaka i kontaktima ordinacije.
- Stranica koristi postojeći Dentaland header, footer, logo, boje i društvene ikonice.
- Dodan je responzivan desktop/mobilni stil u `web/style.css`.
- Link u kartici „Vaši podaci“ sada otvara `privacy.html` u novom tabu uz `rel="noopener"`.
- Uklonjena je apsolutna tvrdnja „Ne dijelimo ih sa trećim stranama“.
- Checkbox sada potvrđuje upoznavanje sa obavještenjem; ne predstavlja se kao univerzalna saglasnost.
- Dodan je browser test `web/tests/privacy.html`.

## Verifikacija

- Playwright/Chromium browser test: PASS, 8/8 provjera.
- Desktop pregled 1440×1000: stranica skroluje; footer je poslije sadržaja, bez preklapanja.
- Mobilni pregled 390×844: `scrollWidth=390`, `clientWidth=390` — nema horizontalnog skrola.
- `git diff --check`: PASS za whitespace/conflict markere; prikazana su samo postojeća LF/CRLF upozorenja.

## Review

```yaml
verdict: PENDING_REVIEW
scope: PENDING
acceptance: PENDING
architecture: PENDING
security: PENDING
blocking_findings: []
```

Nezavisni reviewer nije pokrenut iz ove sesije. Tekst je tehnički implementiran, ali konačnu pravnu potvrdu prije produkcijske objave treba dati pravnik/odgovorno lice ordinacije.

## Integration status

`IMPLEMENTED → VERIFIED → AWAITING_REVIEW/HUMAN_APPROVAL`

## Odbačene opcije

- Univerzalna saglasnost za svu obradu: odbačena jer svaka svrha obrade mora imati odgovarajući pravni osnov.
- Tvrdnja da se podaci ne dijele ni sa kim: odbačena jer ugovoreni hosting/email/tehnički pružaoci mogu biti obrađivači.
- Fiksiranje nepoznatih produkcijskih pružalaca: odbačeno da se ne bi izmišljale činjenice.

## OUT_OF_SCOPE_FINDING

Nema.
