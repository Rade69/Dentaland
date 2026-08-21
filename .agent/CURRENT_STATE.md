# Current State

Last updated: 2026-08-21

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

Nema aktivnog zadatka u toku. Cijeli Prioritet A backloga
(`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`) je sada MERGED:
`DENT-IMPROVE-001` do `006` (Context Debt cleanup, CI, centralne putanje,
Blokiraj vrijeme, Postavke, i sada `006` — dedicated "Novi zahtjevi"
ekran, `RequestsPage` + izdvojen `process_pending_request()` helper
dijeljen sa `DashboardPanels`, implementer Codex, review Claude
PASS_WITH_NOTES). Čeka se Radovanova odluka o Prioritetu B (`007` backup,
`009` Windows packaging) ili drugom prioritetu.

## Agent availability

**Codex ponovo dostupan (od 19.8.2026).** Privremena nedostupnost
(18.8.2026, isticanje kredita) je gotova — uloge se vraćaju na standardnu
raspodjelu: Codex opciono na LOW/MEDIUM implementaciji, obavezan Reviewer 1
na HIGH (uz Crush ili Pi kao Reviewer 2), po tabeli uloga u
`docs/dentaland-agentski-razvoj.md` — kanonski procesni dokument nakon
Faze 2 merge-a (`DENT-AGENT-CONTEXT-002`, MERGED 20.8.2026, tri Codex
review runde). `CLAUDE.md` je sada thin router, ne sadrži tabelu uloga.

## Current verification baseline

Izmjereno 2026-08-21 na `main`, post-merge gate nakon `DENT-IMPROVE-006`:

- `pytest tests/ -q` → **254 passed**, 11 warnings (deprecation warnings iz
  `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda), ~9s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 35
  source files.**

Ne tretirati broj testova kao trajno pravilo — raste sa svakim novim
taskom. Prilikom sljedeće provjere, izmjeriti ponovo, ne kopirati ovaj broj
napamet.

## Active known constraints

- `.codex/hooks.json` postoji ali je njegovo automatsko ponašanje
  **UNVERIFIED** — Claude Code hook (`.claude/settings.json`) je potvrđeno
  automatski aktivan, Codex ekvivalent nije testiran. Ne pretpostaviti da
  Codex automatski blokira konflikt.
- Više paralelnih worktree-ova trenutno postoji pod
  `Dentaland-worktrees/` (npr. `DENT-DESKTOP-*`, `DENT-006` do `DENT-015`)
  — provjeriti `git worktree list` u glavnom repou za tačan trenutni popis
  prije pretpostavke da je neki task završen/aktivan.

## Next known work

Nema otvorenog zadatka — Prioritet A backloga je kompletan. Čeka se
Radovanova odluka o Prioritetu B (`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`:
`DENT-IMPROVE-007` operativni backup, `DENT-IMPROVE-009` Windows
packaging) ili drugom prioritetu.
