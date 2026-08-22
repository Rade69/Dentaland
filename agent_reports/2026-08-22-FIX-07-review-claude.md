---
task_id: FIX-07
reviewer: claude
risk: LOW
verdict: PASS
date: 2026-08-22
---

# Review — FIX-07 (WeekView kartica odsječena na donjoj granici, LOW)

Napomena: ovaj task je već commitovan i pušovan na `main` (`4f47565`)
direktno od strane Codex-a, van uobičajenog Task Contract → worktree →
Claude review → human approval toka ove sesije. Codex-ov vlastiti
"Review" blok u `agent_reports/2026-08-22-FIX-07-weekview-bottom-card.md`
je potpisan `reviewers: [independent-codex]` — nije stvarno nezavisan
review u smislu `CLAUDE.md` (implementer != reviewer, drugi kontekst).
Ovo je taj stvaran nezavisan review, urađen naknadno na Radovanov
zahtjev ("Provjeri ovo što je Codex radio").

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

## Root cause — potvrđeno tačno

`week_view.py::refresh()`: `_cell_span()` klipuje `span` na
`min(span, rowCount() - row)` kad termin počinje blizu donje granice
grida. Prije fixa, `compact` (dvoredna vs troredna kartica) je zavisio
SAMO od stvarnog trajanja (`duration_minutes <= SLOT_MINUTES`), ne od
klipovanog `span`-a — termin 19:00–20:30 (90 min, span klipovan na 1) je
dobijao troredni prikaz u ćeliji visine samo jednog reda → odsijecanje.

Fix: `compact = duration_minutes <= self.SLOT_MINUTES or span == 1` —
minimalan, jednolinijski, tačno adresira uzrok.

## Adversarna provjera (nezavisna reprodukcija)

1. Privremeno vratio staro ponašanje (`compact = duration_minutes <=
   self.SLOT_MINUTES`, bez `or span == 1`) → novi test
   `test_termin_preko_donje_granice_koristi_kompaktnu_karticu` **PADA**
   (`assert False is True`). Vraćeno preko `git checkout --` (bezbjedno
   — commitovano u historiji).
2. Pun `tests/test_gui/test_week_view.py` (24 testa) → sve PASS,
   uključujući postojeći `test_termin_od_90_min_je_spojen_preko_dva_satna_slota`
   (90-min termin NE na donjoj granici i dalje ispravno dobija
   `rowSpan==2`/netaknuto — potvrđuje da fix ne prekomjerno okida
   compact za normalne slučajeve).
3. Pun `pytest tests/ -q` na trenutnom `main` (uključuje i FIX-08) →
   285 passed. `ruff`/`mypy` čisti.

## Zaključak

Fix je ispravan, minimalan, adversarno potvrđen. **PASS.** Scope čist
(samo `week_view.py` produkcijska izmjena + test).

## Handoff

```text
CILJ: Termin koji prelazi donju granicu WeekView-a koristi kompaktan
      prikaz umjesto odsječenog troredog.
URAĐENO: PASS — root cause tačan, fix minimalan, adversarno potvrđen.
NE DIRATI: ostatak week_view.py, ostali fajlovi — nedirano.
SLJEDEĆE: Već je na main/origin — nema dalje akcije osim ažuriranja
      statusa u agent_reports/.
```
