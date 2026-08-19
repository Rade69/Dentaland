---
task_id: DENT-AGENT-CONTEXT-001
risk: LOW
implementer: claude
reviewers: []
verdict: PENDING
commits: []
created_at: 2026-08-19T15:46:31Z
---

# DENT-AGENT-CONTEXT-001 — Faza 1: `.agent/` navigacioni sloj

## Task Contract

```yaml
id: DENT-AGENT-CONTEXT-001
title: "Faza 1 — dodati .agent/ navigacioni sloj (bez izmjene postojećih pravila)"
risk: LOW
objective: >
  Dodati četiri nova fajla (.agent/PROJECT_MAP.md, CURRENT_STATE.md,
  TASK_ROUTING.md, CONTEXT_LOADING.md) koji fresh agentu daju brzu
  orijentaciju kroz repo i razdvajaju trajna pravila od kratkotrajnog
  stanja — bez diranja CLAUDE.md/AGENTS.md ili bilo kog postojećeg
  procesa (Task Contract, worktree, coordination.py, Reviewer Context
  Pack, structured verdict, Implementer != Reviewer).
allowed_paths: [.agent/, agent_reports/2026-08-19-DENT-AGENT-CONTEXT-001-faza1-agent-mapa.md]
forbidden_paths: [CLAUDE.md, AGENTS.md, src/, desktop/, backend/, web/, migrations/, docs/]
acceptance:
  - .agent/PROJECT_MAP.md odgovara stvarnoj strukturi repoa (provjereno find/ls, ne pretpostavljeno)
  - .agent/CURRENT_STATE.md sadrži svjež (2026-08-19) test/lint/mypy baseline, ne kopiran stari broj
  - .agent/TASK_ROUTING.md referencira postojeće globalne skillove (prime-bug/prime-feature/independent-review), ne duplira ih
  - CLAUDE.md i AGENTS.md ostaju bajt-identični (git diff prazan)
verification: [pytest tests/ -q, ruff check src/dentaland desktop backend tests, mypy src/dentaland desktop backend]
review:
  reviewers: 1
  required: [scope, accuracy — da li mapa stvarno odgovara kodu]
```

Kontekst: implementacija prijedloga iz
`C:\Users\38765\Downloads\IndyDevDen-AI-inženjering\DENTALAND_AGENT_READY_WORKFLOW_MIGRATION_GUIDE.md`
(vodič, van repoa), namjerno ograničena SAMO na Fazu 1 (aditivni `.agent/`
sloj). Faza 2 (konsolidacija `docs/dentaland-agentski-razvoj.md` +
stanjenje `CLAUDE.md`/`AGENTS.md`) je namjerno odvojena u poseban budući
task/Task Contract — vodič predlaže jedan veliki zadatak za sve, ovdje je
namjerno razdvojeno da bi se rizičniji, teže reverzibilan korak (diranje
fajlova koje svaki agent čita prvi) validirao odvojeno, nakon što se
potvrdi da sami `.agent/` fajlovi pomažu.

## Šta je urađeno

Kreiran worktree `Dentaland-worktrees/DENT-AGENT-CONTEXT-001` (grana
`task/DENT-AGENT-CONTEXT-001`, iz `main` @ `e8e1778`).

Dodana četiri fajla u `.agent/`:

- **`PROJECT_MAP.md`** — mapa stvarne strukture repoa (entry points, domain
  model, booking/requests/notifications/printing domene, desktop GUI sa
  read-next navigacijom, web/javna forma, agent workflow, arhitektura, run
  locally). Struktura provjerena direktno (`find`/`ls`), ne prepisana iz
  vodiča — otkrivena je i ispravljena jedna netačnost u samom procesu
  pisanja: `desktop/views/dialogs/` je stvaran poddirektorijum sa šest
  fajlova (`appointment_details.py`, `appointment_editor.py`,
  `base_dialog.py`, `cancel_appointment.py`, `move_appointment.py`,
  `process_request.py`), ne prazna pretpostavka — moja prva `find -maxdepth
  2` komanda ga je propustila zbog dubine, ispravljeno prije finalizacije
  fajla.
- **`CURRENT_STATE.md`** — trenutni fokus (`DENT-DESKTOP-F`, hard delete
  termina, HIGH, plan napisan, implementacija još nije počela — potvrđeno
  čitanjem `agent_reports/2026-08-19-DENT-DESKTOP-F-plan.md` i provjerom da
  fajlovi iz plana još ne postoje), agent availability (Codex nedostupan od
  18.8.2026, prepisano iz `CLAUDE.md` kao primjer kratkotrajne informacije
  koja pripada ovdje), i svjež verification baseline (vidi ispod).
- **`TASK_ROUTING.md`** — read-set po tipu zadatka (bug, feature, Desktop
  GUI, Booking/service, Schema/migration HIGH-risk, Public web/API,
  Review) — eksplicitno referencira globalne skillove `prime-bug`,
  `prime-feature`, `independent-review`, ne duplira njihovu logiku, samo
  daje Dentaland-specifičan routing paket.
- **`CONTEXT_LOADING.md`** — kratka operativna politika (default ne čitaj
  široko, start-set, expand-only-on-evidence, stop rule).

## Verifikacija

Pokrenuto svježe u worktree-u, 2026-08-19, na neizmijenjenom kodu (samo
`.agent/` dodano, kod netaknut):

```text
pytest tests/ -q
→ 202 passed, 11 warnings in 12.02s

ruff check src/dentaland desktop backend tests
→ All checks passed!

mypy src/dentaland desktop backend
→ Found 6 errors in 2 files (checked 29 source files)
   desktop/views/week_view.py:108,493,503 — missing type annotation (x3) + QTableWidget.DragDrop stub gap
   desktop/views/main_window.py:52,540 — missing type annotation (x2)
```

Sve 6 mypy grešaka su postojeći baseline problemi (nisu uvedeni ovim
zadatkom — `.agent/` fajlovi su čista dokumentacija, dodavanje im nije
moglo uticati na mypy nalaze u `desktop/`). Zapisano u `CURRENT_STATE.md`
kao "trenutni baseline", eksplicitno označeno da se ne tretira kao trajno
pravilo o broju testova.

`git diff --stat -- CLAUDE.md AGENTS.md` → prazno (potvrđeno, nulta izmjena).
`git status --short` → samo `?? .agent/` (novi, untracked fajlovi).

## Review

```yaml
verdict: PENDING
scope: NOT_REVIEWED
accuracy: NOT_REVIEWED
blocking_findings: []
```

Nije rađen nezavisan review — ovaj izvještaj piše Implementer (ista sesija
koja je pisala fajlove). Po pravilu "Implementer nikad nije isti
agent/sesija kao Reviewer", potreban je nezavisan pregled (Crush ili Pi,
Codex trenutno nedostupan) prije nego što se ovo tretira kao završeno —
ili direktan pregled od strane Radovana s obzirom da je risk LOW i obim
mali (samo 4 nova markdown fajla + ovaj report, nula izmjena postojećeg
koda/pravila).

## Integration status

`NOT_MERGED` — nije commitovano (po pravilu: agent ne commituje bez
eksplicitnog zahtjeva korisnika). Worktree `Dentaland-worktrees/
DENT-AGENT-CONTEXT-001` postoji i sadrži izmjene, spreman za pregled.

## Odbačene opcije

| Opcija | Zašto razmatrana | Zašto odbačena | Kad ponovo otvoriti |
|---|---|---|---|
| Uraditi cijeli vodič odjednom (sve faze, uključujući konsolidaciju docs-a i stanjenje CLAUDE.md/AGENTS.md) | Vodič to predlaže kao jedan zadatak | Veći, teže reverzibilan zahvat na fajlovima koje svaki agent čita prvi; bolje validirati korist samih `.agent/` fajlova prije nego što se dira postojeći, stabilan proces | Kad se Faza 1 potvrdi kao korisna kroz par stvarnih taskova (vidi "Sljedeće" ispod) |

## OUT_OF_SCOPE_FINDING

Nema — nije primijećeno ništa van obima tokom rada.

## Sljedeće

1. Nezavisan review ovog malog dodatka (Crush/Pi ili Radovan direktno).
2. Ako se odobri: commit (na eksplicitan zahtjev), zatim probati na 1-2
   stvarna taska (npr. sljedeći GUI ili service task) da se vidi da li
   `.agent/` fajlovi stvarno smanjuju lutanje — prije nego što se ide na
   Fazu 2 (konsolidacija `docs/dentaland-agentski-razvoj.md` + stanjenje
   `CLAUDE.md`/`AGENTS.md`), koja je namjerno ostavljena kao poseban,
   budući Task Contract.
