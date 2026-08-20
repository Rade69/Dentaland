---
task_id: DENT-IMPROVE-002
risk: LOW
implementer: pi
reviewers: [claude]
verdict: PASS_WITH_NOTES
status: MERGED_INTEGRATION_VERIFIED
commits: [4439b55]
created_at: 2026-08-20
---

## Integration status

`MERGED → INTEGRATION_VERIFIED → DONE` (20.8.2026). Review: Claude
`PASS_WITH_NOTES` (`agent_reports/2026-08-20-DENT-IMPROVE-002-review-claude.md`).
Human approval: Radovan ("popravi i onda komituj i merdžuj"). Merge
commit na `main` (`--no-ff`). Post-merge gate: `pytest` → 222 passed,
`ruff` → All checks passed, `mypy` → 0 grešaka (31 fajlova). Pravi GitHub
Actions run se potvrđuje nakon prvog push-a na remote — ostaje otvoreno
kao rezidualni rizik (apt paket lista za PySide6 headless).

# DENT-IMPROVE-002 — GitHub Actions CI

## Task Contract

**Cilj:** Automatski pokretati `pytest`, `ruff` i `mypy` na GitHubu za svaki
push/PR — trenutno te provjere postoje samo lokalno.

**Risk:** LOW

**Izvor:** `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 3
(`DENT-IMPROVE-002`) — sekcija sadrži pun detalj (workflow koraci,
constraints, acceptance) ako zatreba, ali NEMOJ je čitati prije nego
pokušaš sam odrediti put kroz `.agent/TASK_ROUTING.md` i
`.agent/PROJECT_MAP.md`. Prvo pokušaj sa AGENTS.md/CLAUDE.md → `.agent/`
slojem, backlog dokument koristi tek ako ti nešto ostane nejasno.

**Allowed paths:** `.github/workflows/`, `README.md` (i `pyproject.toml`
samo ako je nužno, uz eksplicitno obrazloženje zašto).

**Forbidden paths:** `src/`, `desktop/`, `backend/`, `web/`, `migrations/`.

**Acceptance:**
- workflow se pokreće na `push` i `pull_request`,
- sve tri provjere (`pytest`, `ruff`, `mypy`) prolaze u CI-ju na trenutnom
  `main`,
- CI koristi Python verziju usklađenu sa projektom,
- README kratko navodi CI,
- bez matrixa na više Python verzija, bez Dockera, bez coverage gate-a
  (nije projektni standard).

**Verification:** GitHub Actions run zelen; lokalno i dalje `pytest tests/
-q`, `ruff check`, `mypy` prolaze bez promjene.

**Review:** Claude, nezavisan od implementera.

## Probni signal — obavezno u `agent_report`

Prije prve izmjene, kratko zapiši (par redova, ne poseban dokument):
- koliko fajlova si pročitao prije prve izmjene,
- da li si koristio `.agent/PROJECT_MAP.md` / `.agent/TASK_ROUTING.md`,
- da li si tražio dodatno pojašnjenje strukture repoa,
- da li si ostao u `allowed_paths`.

Ovo je nastavak probnog mjerenja da li `.agent/` sloj stvarno pomaže —
vidi `agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md`
za dosadašnje nalaze. Ovaj task je prva prilika da se izmjeri na potpuno
novom tipu zadatka (CI/tooling), koji dosad nije bio testiran.
