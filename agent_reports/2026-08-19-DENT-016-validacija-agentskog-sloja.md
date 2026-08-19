# DENT-016 — Validacija `.agent/` navigacionog sloja (probni task)

Task: DENT-016 | Implementer: crush | Datum: 2026-08-19

## Zapis o navigaciji (prije prve izmjene koda)

- **Fajlovi pročitani prije prve izmjene:**
  - `agent_reports/DENT-016-task-contract.md` (pun Task Contract)
  - `.agent/PROJECT_MAP.md` + `.agent/TASK_ROUTING.md` — ali tek NAKON što
    sam ih ručno pronašao u `Dentaland-worktrees/DENT-AGENT-CONTEXT-001/.agent/`,
    jer **NE postoje u `main`** (niti u mom novom worktree-u).
- **Koristio `.agent/`?** DA (PROJECT_MAP + TASK_ROUTING), ali ne kroz
  standardni tok — morao sam prvo `git worktree list` + `ls .agent` (main,
  prazno) pa `ls` u DENT-AGENT-CONTEXT-001 worktree-u da ih nađem.
- **Pitao za pojašnjenje strukture?** NE — sam pronašao (uz 2-3 dodatna
  istraživačka poziva).

## Ključni nalaz (validacija sloja)

`.agent/` navigacioni sloj **nije merge-ovan u `main`**. Standardni workflow
(`git worktree add ... main`) kreira worktree BEZ `.agent/`, pa agent koji
radi po uputstvu "pročitaj `.agent/PROJECT_MAP.md`" dobije `FileNotFound`
i mora ručno lutati po worktree-ovima. Ovo je upravo ono što sloj treba da
eliminiše — referentna vrijednost (before) bila je 6 istraživačkih poziva,
a ja sam potrošio 3 poziva SAMO da nađem `.agent/` (nije u main).

## DENT-016 status

Implementacija je **već merge-ovana u `main`** (iz ranijeg DENT-016 rada):
`desktop/print_document.py`, `desktop/views/main_window.py::_on_print`
(+ `_print_week`/`_print_day`/`_save_pdf`/`_pick_day`) i
`tests/test_gui/test_print_document.py` sve postoje u novom worktree-u.
Nema nove implementacije — task je čisto validacioni.

## TASK_ROUTING.md validaciona tabela

Nije popunjena: `.agent/TASK_ROUTING.md` je u grani
`task/DENT-AGENT-CONTEXT-001` (tuđa aktivna grana, nije merge-ovana u `main`),
pa je ne diram bez koordinacije. Zapis je ovdje u `agent_reports/`.
