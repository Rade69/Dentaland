# Current State

Last updated: 2026-08-20

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

Nema aktivnog zadatka u toku — svih 6 faza desktop redizajna (A–F),
`DENT-DESKTOP-F`, Faza 2 agentskog workflow-a i `DENT-020` (email reminder
scheduler) su svi MERGED. Čeka se Radovanova odluka o sljedećem
prioritetu (kandidati: Viber integracija — plan eksplicitno kaže "tek
nakon što osnovni booking/email tok radi stabilno", RBAC/auth,
PostgreSQL migracija, ili nešto sitno frontend/GUI za sljedeći
implementacioni probni signal).

## Agent availability

**Codex ponovo dostupan (od 19.8.2026).** Privremena nedostupnost
(18.8.2026, isticanje kredita) je gotova — uloge se vraćaju na standardnu
raspodjelu: Codex opciono na LOW/MEDIUM implementaciji, obavezan Reviewer 1
na HIGH (uz Crush ili Pi kao Reviewer 2), po tabeli uloga u
`docs/dentaland-agentski-razvoj.md` — kanonski procesni dokument nakon
Faze 2 merge-a (`DENT-AGENT-CONTEXT-002`, MERGED 20.8.2026, tri Codex
review runde). `CLAUDE.md` je sada thin router, ne sadrži tabelu uloga.

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

- `DENT-DESKTOP-F` — hard delete termina (HIGH). MERGED, integration
  verified (`1e3c6c0`). Svih 6 faza desktop redizajna (A–F) završeno.
- `DENT-AGENT-CONTEXT-002` (Faza 2 agentskog workflow-a) — konsolidacija
  `docs/dentaland-agentski-razvoj.md` (sada kanonski procesni dokument) +
  stanjenje `CLAUDE.md` (296→119 linija). Tri Codex review kruga, MERGED.
- `DENT-016`–`DENT-019` — probni ciklusi 1-2 (`.agent/` validacija
  implementacije/bug-fix zadataka kod Crush i Pi) — ZAKLJUČENO, koncept
  potvrđen (0 istraživačkih poziva naspram 6 baseline).
- `DENT-020` — in-process email reminder scheduler (Codex, prvi
  implementacioni probni signal za njega). MERGED → INTEGRATION_VERIFIED
  → DONE (20.8.2026). Codex JE koristio `.agent/PROJECT_MAP.md`/
  `TASK_ROUTING.md` kad je bio implementer sa kratkim promptom —
  razriješilo neizvjesnost iz Faze 2 review krugova (redundantnost tamo je
  bila zbog previše detaljnog task brief-a, ne zbog agenta ili tipa
  zadatka). Vidi `TASK_ROUTING.md` finalni nalaz.

## Next known work

Nema otvorenog zadatka — čeka se Radovanova odluka o sljedećem prioritetu.
Post-merge gate na `main` (20.8.2026): pytest 222 passed, ruff clean, mypy
clean (0 issues, 31 fajlova).
