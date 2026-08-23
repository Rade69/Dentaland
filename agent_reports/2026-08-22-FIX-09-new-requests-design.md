---
task_id: FIX-09
risk: LOW
implementer: codex
reviewers: [independent]
verdict: PASS_WITH_NOTES
commits: []
created_at: 2026-08-22
---

# FIX-09 — novi dizajn stranice „Novi zahtjevi“

## Task Contract

Vidi [FIX-09-task-contract.md](FIX-09-task-contract.md).

## Implementacija

Postojeća `RequestsPage` je vizuelno usklađena sa dostavljenom referencom:
summary kartica, kartice zahtjeva sa inicijalima i razdvojenim metapodacima,
oznaka `NOVO`, naglašeno dugme `Obradi`, dekorativna tri-tačka oznaka i donji
savjet. Prazno stanje je dobilo zasebnu karticu. Poslovni tok ostaje postojeći
`process_pending_request` bez izmjena.

Vrijeme slanja prikazuje `danas u HH:MM` za zahtjev iz današnjeg lokalnog dana,
a za starije zahtjeve zadržava puni datum i vrijeme u zoni Europe/Sarajevo.

## Verifikacija implementera

- `pytest tests/test_gui/test_requests_page.py tests/test_gui/test_main_window.py`
  → **36 passed**.
- `pytest tests` → **287 passed**, 11 postojećih dependency/deprecation
  upozorenja.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 36
  source files**.
- Qt offscreen render 1250×760 →
  `C:/Users/38765/Desktop/Dentaland/output/fix09-new-requests.png`.

Smoke render potvrđuje raspored, boje i da četiri kartice staju bez
horizontalnog preklapanja. Trenutni izolovani Qt proces nije imao nijednu
dostupnu sistemsku font familiju (`QFontDatabase.families() == []`), pa se
tekst na smoke screenshotu prikazuje tofu znakovima; tekstualni sadržaj i
objektna struktura pokriveni su determinističkim pytest testovima.

## Scope

Dirnuti su samo `requests_page.py`, njegovi testovi i FIX-09 izvještaji.
`main_window.py` je ostao neizmijenjen iako je bio dozvoljen contractom.

## Nezavisni review

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Reviewer je nezavisno dobio **51 passed** na ciljanom GUI paketu i **287
passed** na punom paketu; ruff i projektni mypy takođe prolaze. Na 1536×760
i 1250×760 potvrdio je četiri vidljive kartice i dugmeta, summary i savjet,
bez horizontalnog ili vertikalnog overflowa. Potvrđeni su i prazno stanje i
nepromijenjen zajednički tok obrade.

Neblokirajuća napomena: pri zahtijevanoj širini 800/640 widget zadržava
postojeći minimum oko 1069 px i skriveni horizontalni scrollbar dobija
`maximum=59`. To ne krši desktop acceptance na 1536×760; puna responsivnost
na veoma uskom prozoru može biti zaseban LOW zadatak.
