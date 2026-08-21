# Current State

Last updated: 2026-08-21

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

Nema aktivnog zadatka u toku. Pored ranije MERGED rada (6 faza desktop
redizajna, Faza 2 agentskog workflow-a, `DENT-020`), sada su MERGED i
`DENT-IMPROVE-001` do `004` (Context Debt cleanup, CI, centralne putanje,
Blokiraj vrijeme) i `DENT-IMPROVE-005` (minimalne Postavke —
`SettingsPanel`: doktori aktivan/neaktivan, usluge dodaj/uredi, radno
vrijeme split shift; implementer Crush, review Claude PASS_WITH_NOTES,
adversarno testirani touching-boundary/prazna-lista/po-danu-izolacija
slučajevi). Sljedeći u redu: `DENT-IMPROVE-006` (Novi zahtjevi ekran) —
koordinaciona napomena: dira iste navigacione fajlove kao `004`/`005`
(već MERGED), nema više konflikta na čekanju.

## Agent availability

**Codex ponovo dostupan (od 19.8.2026).** Privremena nedostupnost
(18.8.2026, isticanje kredita) je gotova — uloge se vraćaju na standardnu
raspodjelu: Codex opciono na LOW/MEDIUM implementaciji, obavezan Reviewer 1
na HIGH (uz Crush ili Pi kao Reviewer 2), po tabeli uloga u
`docs/dentaland-agentski-razvoj.md` — kanonski procesni dokument nakon
Faze 2 merge-a (`DENT-AGENT-CONTEXT-002`, MERGED 20.8.2026, tri Codex
review runde). `CLAUDE.md` je sada thin router, ne sadrži tabelu uloga.

## Current verification baseline

Izmjereno 2026-08-21 na `main`, post-merge gate nakon `DENT-IMPROVE-005`:

- `pytest tests/ -q` → **251 passed**, 11 warnings (deprecation warnings iz
  `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda), ~12s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 34
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

`DENT-IMPROVE-006` (Novi zahtjevi ekran) je pripremljen
(`agent_reports/DENT-IMPROVE-006-task-contract.md`), čeka dodjelu
implementeru. Ovo je posljednja stavka iz Prioriteta A backloga
(`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`) — nakon nje Prioritet B
(`007` backup, `009` packaging).
