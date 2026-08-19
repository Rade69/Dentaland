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

Codex privremeno nedostupan (od 18.8.2026, isticanje kredita). Dok se ne
obnovi: Codex se ne dodjeljuje kao Implementer ni Reviewer ni na jednom
novom zadatku. Na HIGH zadacima, oba mjesta Reviewer 1/2 popunjavaju Crush i
Pi (umjesto uobičajenog Codex + jedan od njih). Ovo NIJE trajna promjena
procesa — kad se Codex vrati, uloge se vraćaju na raniju raspodjelu (vidi
`AGENTS.md`/`CLAUDE.md` tabelu uloga za trajno pravilo, ovo je samo trenutni
status dostupnosti).

## Current verification baseline

Izmjereno 2026-08-19 na `main` (commit `e8e1778`):

- `pytest tests/ -q` → **202 passed**, 11 warnings (deprecation warnings iz
  `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda), 12.02s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **6 errors, 2 files** — poznat
  baseline, ne novi problem uveden ovom migracijom:
  - `desktop/views/week_view.py:108,493,503` — nedostaje type annotation na
    parametrima (3x), i `QTableWidget` nema `DragDrop` atribut (PySide6
    stub gap, ne stvaran bug).
  - `desktop/views/main_window.py:52,540` — nedostaje type annotation na
    parametrima (2x).

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
- `DENT-DESKTOP-F` — hard delete termina. Implementacija + oba review-a
  PASS, čeka human approval (vidi "Current development focus" iznad).

## Next known work

- Human approval za `DENT-DESKTOP-F` (Radovanova odluka, ne agentski posao).
- `DENT-016`/`DENT-017` implementacija (Crush/Pi) — vidi "Current
  development focus".
