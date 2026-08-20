# Current State

Last updated: 2026-08-19

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

`DENT-DESKTOP-F` — hard delete termina. Risk: HIGH. Implementer: Claude
direktno. Reviewer 1/2: Crush i Pi, nezavisno.

Status na 2026-08-19 (ažurirano — prethodni unos ovdje je bio zastario
nakon par sati): implementacija ZAVRŠENA, **oba reviewera dala `verdict:
PASS`** (`agent_reports/2026-08-19-DENT-DESKTOP-F-review-crush.md`,
`-review-pi.md`). Čeka SAMO human approval (Radovan) prije merge-a — ovo
NIJE moj task za implementaciju niti review, samo za praćenje statusa.

`DENT-016` (Crush, MEDIUM) i `DENT-017` (Pi, LOW) — kontrakti spremni
(`agent_reports/DENT-016-task-contract.md`, `DENT-017-task-contract.md`),
proslijeđeni agentima, worktree-ovi još nisu otvoreni za njih. Oba su i
probni taskovi za `.agent/` validacionu tabelu (vidi `TASK_ROUTING.md`).

## Agent availability

**Codex ponovo dostupan (od 19.8.2026).** Privremena nedostupnost
(18.8.2026, isticanje kredita) je gotova — uloge se vraćaju na standardnu
raspodjelu: Codex opciono na LOW/MEDIUM implementaciji, obavezan Reviewer 1
na HIGH (uz Crush ili Pi kao Reviewer 2), po tabeli uloga u `CLAUDE.md`
(uskoro `docs/dentaland-agentski-razvoj.md`, čeka merge Faze 2 —
`DENT-AGENT-CONTEXT-002`, pending review).

## Current verification baseline

Izmjereno 2026-08-19 na `main`, nakon DENT-018/019 (mypy cleanup, drugi
probni krug):

- `pytest tests/ -q` → **206 passed**, 11 warnings (deprecation warnings iz
  `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda), ~10s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 29
  source files.** Ranijih 6 grešaka (week_view.py, main_window.py) su bile
  poznat baseline, riješene kroz DENT-018 (Crush) i DENT-019 (Pi) — čist
  mypy sada, ne samo baseline bez novih problema.

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

## Recently completed major work

- `DENT-DESKTOP-B3` — ikonica u zaglavlju dijaloga + prozorska ikonica.
  MERGED, integration verified (commit `21ef806`).
- `DENT-016`/`DENT-017` — probni ciklus 1 (štampa se ispostavila već
  gotova; email podsjetnik implementiran, PASS, MERGED).
- `DENT-018`/`DENT-019` — probni ciklus 2 (mypy cleanup, oba MERGED,
  `mypy` sada potpuno čist). `.agent/` validacija ZAKLJUČENA: koncept
  potvrđen (0 istraživačkih poziva u oba drugog-kruga taska, naspram 6 u
  before baseline-u) — vidi `TASK_ROUTING.md` finalni nalaz.

## Next known work

- Human approval za `DENT-DESKTOP-F` (Radovanova odluka, ne agentski
  posao) — i dalje čeka, blokiran na merge nivou (sistemski blok, ne
  proceduralni razlog).
- Faza 2 (konsolidacija `docs/dentaland-agentski-razvoj.md` + stanjenje
  `CLAUDE.md`/`AGENTS.md`) — sada otvorena za planiranje, `.agent/`
  validacija je gotova. Zaseban budući Task Contract, kad Radovan odluči
  da je prioritet.
