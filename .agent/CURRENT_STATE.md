# Current State

Last updated: 2026-08-20

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

Nema aktivnog zadatka u toku. Pored ranije MERGED rada (6 faza desktop
redizajna, Faza 2 agentskog workflow-a, `DENT-020`), sada su MERGED i
`DENT-IMPROVE-001` (Context Debt cleanup), `DENT-IMPROVE-002` (GitHub
Actions CI, implementer Pi) i `DENT-IMPROVE-003` (centralne
runtime/data/resource putanje — `src/dentaland/paths.py`, implementer Pi,
review Claude PASS_WITH_NOTES). Sljedeći u redu: `DENT-IMPROVE-004`
(Blokiraj vrijeme) — koordinaciona napomena u Task Contractu: dira iste
navigacione fajlove (`main_window.py`/`sidebar.py`) kao `005`/`006`,
preporučen strogo sekvencijalni redoslijed `004 → 005 → 006`.

## Agent availability

**Codex ponovo dostupan (od 19.8.2026).** Privremena nedostupnost
(18.8.2026, isticanje kredita) je gotova — uloge se vraćaju na standardnu
raspodjelu: Codex opciono na LOW/MEDIUM implementaciji, obavezan Reviewer 1
na HIGH (uz Crush ili Pi kao Reviewer 2), po tabeli uloga u
`docs/dentaland-agentski-razvoj.md` — kanonski procesni dokument nakon
Faze 2 merge-a (`DENT-AGENT-CONTEXT-002`, MERGED 20.8.2026, tri Codex
review runde). `CLAUDE.md` je sada thin router, ne sadrži tabelu uloga.

## Current verification baseline

Izmjereno 2026-08-20 na `main`, post-merge gate nakon `DENT-IMPROVE-003`:

- `pytest tests/ -q` → **229 passed**, 11 warnings (deprecation warnings iz
  `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda), ~10s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 32
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

`DENT-IMPROVE-004` (Blokiraj vrijeme) je pripremljen
(`agent_reports/DENT-IMPROVE-004-task-contract.md`), čeka dodjelu
implementeru. Nakon njega: `005` (Postavke), pa `006` (Novi zahtjevi
ekran) — vidi koordinacionu napomenu iznad.
