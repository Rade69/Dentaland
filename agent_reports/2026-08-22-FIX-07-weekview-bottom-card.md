---
task_id: FIX-07
risk: LOW
implementer: codex
reviewers: [independent-codex]
verdict: PASS_WITH_NOTES
commits: []
created_at: 2026-08-22
---

# FIX-07 — WeekView kartica odsječena na donjoj granici

## Task Contract

Vidi [FIX-07-task-contract.md](FIX-07-task-contract.md).

## Šta je urađeno

Termin koji prelazi donju granicu WeekView-a sada koristi kompaktni dvoredni
prikaz kada mu je dostupan samo jedan vidljivi red. Stvarno vrijeme termina
ostaje prikazano; broj redova, granica 20:00 i logika zakazivanja nisu
mijenjani.

## Reprodukcija prije popravke

Termin `19:00–20:30` mapirao se na posljednji red sa `span=1`, ali je dobijao
`compact=False` i dva `<br>` (tri reda sadržaja). Novi regresioni test je prije
izmjene padao na `assert card.property("compact") is True`.

## Verifikacija implementera

- Tačan repro poslije popravke → **1 passed**.
- `pytest tests/test_gui/test_week_view.py tests/test_gui/test_week_view_combined.py`
  → **29 passed**.
- `pytest tests -q -p no:cacheprovider` → **273 passed**, 11 postojećih
  dependency/deprecation upozorenja u trenutku implementer provjere.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 35
  source files**.
- Qt offscreen render → `output/fix07-weekview-bottom.png`; kartica ostaje
  unutar donje ivice. Offscreen okruženje nema ispravan Unicode font, pa je
  screenshot korišten za layout, a tekst je potvrđen determinističkim testom.

## Review

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisni reviewer je reprodukovao stari kvar učitavanjem HEAD modula
(`span=1`, `compact=False`, dva `<br>`) i novi rezultat (`span=1`,
`compact=True`, jedan `<br>`, vrijeme 19:00–20:30 sačuvano). Adversarni termin
09:00–10:30 ostaje `span=2`, `compact=False` i dva `<br>`. Reviewer je
nezavisno dobio 29 WeekView testova i, na tadašnjem stanju dijeljenog tree-a,
277 testova u punom suite-u, Ruff PASS, mypy PASS i `git diff --check` PASS.

Neblokirajuća napomena: postojeći test za 09:00–10:30 eksplicitno potvrđuje
`rowSpan == 2`, dok je `compact=False`/dva `<br>` potvrđeno živim reviewerskim
reproom, ne posebnom assertion stavkom.

## Integration status

Nije commitovano niti merge-ovano; čeka human approval/commit.

## Odbačene opcije

- Produžiti WeekView do 21:00 — odbačeno jer bi promijenilo granice cijelog
  rasporeda umjesto da popravi prezentaciju na postojećoj granici.
- Skraćivati prikazano vrijeme na 20:00 — odbačeno jer bi prikazivalo netačne
  podatke o stvarnom završetku termina.

## OUT_OF_SCOPE_FINDING

Nema.
