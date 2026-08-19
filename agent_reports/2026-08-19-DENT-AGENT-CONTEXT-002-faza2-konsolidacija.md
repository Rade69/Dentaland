---
task_id: DENT-AGENT-CONTEXT-002
risk: MEDIUM
implementer: claude
reviewers: []
verdict: PENDING
commits: []
created_at: 2026-08-19T00:00:00Z
---

# DENT-AGENT-CONTEXT-002 — Faza 2: konsolidacija + thin router

Kontekst: nastavak `DENT-AGENT-CONTEXT-001` (Faza 1, validirana kroz dva
probna kruga — vidi `.agent/TASK_ROUTING.md` finalni nalaz). Plan prije
izmjene: `2026-08-19-DENT-AGENT-CONTEXT-002-plan.md` u istom folderu.

## Before

Prije ove izmjene, agent koji počinje rad na Dentalandu je morao:

- Pročitati `AGENTS.md`, koji je govorio "pročitaj `CLAUDE.md` u
  cijelosti" — 296 linija koje miješaju projektne premise (šta je
  Dentaland, arhitektura, sigurnost) sa procesnim pravilima (Task
  Contract, uloge, review format).
- `docs/dentaland-agentski-razvoj.md` je postojao paralelno, ali zastario
  — koristio binarni "kritičan da/ne" umjesto LOW/MEDIUM/HIGH,
  "Reviewer 2: Codex" fiksno (bez Crush/Pi tabele ni napomene o
  nedostupnosti), i imao neaktivnu numeraciju zadataka (0.1–M1.3,
  potvrđeno `grep`-om: 0 pogodaka u 48 postojećih `DENT-XXX` taskova).
  Sam `CLAUDE.md` je tvrdio da JE noviji izvor — dva dokumenta, jedan
  eksplicitno kaže da je drugi zastario, ali oba i dalje postoje.

## Changed

- **`docs/dentaland-agentski-razvoj.md`** (172 → 401 linija): postaje
  kanonski procesni dokument. Primio ažuran sadržaj iz `CLAUDE.md` (risk
  tabela LOW/MEDIUM/HIGH, uloge sa Crush/Pi/Claude, Task Contract format
  sa `allowed_paths`/`forbidden_paths`, ownership/coordination preko
  `scripts/coordination.py`, Reviewer Context Pack, strukturiran verdikt,
  7-stavna hijerarhija autoriteta, `OUT_OF_SCOPE_FINDING`, hijerarhija
  dokaza, Post-merge Integration Gate, Evidence paket, Facts vs
  Decisions). Napuštena fazna numeracija (0.1–M1.3) premještena na dno kao
  jasno označen "Istorijski dodatak — NEAKTIVNO, samo referenca" (nije
  obrisana bez potvrde — vidi Odbačene opcije u plan fajlu).
- **`CLAUDE.md`** (296 → 119 linija, -60%): zadržava SAMO projektni
  sadržaj (šta je Dentaland, jezik, klijent/razmjer, arhitektura, šta se
  ne gradi, sigurnost/privatnost, otvorena pitanja) — ovo je "šta je
  projekat", ne "kako se radi", pa ostaje ovdje. Dodana "Start here"
  navigacija na vrh (`AGENTS.md` → `.agent/PROJECT_MAP.md` → Task
  Contract → `.agent/TASK_ROUTING.md`) i "Non-negotiable global rules"
  kratka lista + pokazivač na `docs/dentaland-agentski-razvoj.md` za pun
  proces. "Izvori istine" sekcija ažurirana — više ne tvrdi da je
  `CLAUDE.md` operativni izvor za proces.
- **`AGENTS.md`**: početna instrukcija promijenjena sa "pročitaj
  `CLAUDE.md` u cijelosti" na kraću navigaciju (`CLAUDE.md` thin router →
  `.agent/PROJECT_MAP.md` → Task Contract → `.agent/TASK_ROUTING.md` →
  `docs/dentaland-agentski-razvoj.md` za pun proces).
- Samo premještanje/deduplikacija — **nijedna semantika pravila nije
  promijenjena.**

## Preserved

Eksplicitno provjereno da je OSTALO isto (ne samo tvrdnja):

- Implementer != Reviewer, worktree per task, Task Contract format,
  ownership/coordination (`scripts/coordination.py`), Reviewer Context
  Pack, strukturiran verdikt (`verdict/scope/acceptance/architecture/
  security/blocking_findings`), 7-stavna hijerarhija autoriteta,
  `OUT_OF_SCOPE_FINDING`, Post-merge Integration Gate, Evidence paket,
  Facts vs Decisions format, risk-tier proces (LOW/MEDIUM/HIGH).
- Sve projektne premise iz `CLAUDE.md` (arhitektura, sigurnost/
  privatnost, šta se ne gradi) — prenesene bez izmjene teksta.
- `.agent/` sloj (Faza 1) — netaknut.
- Istorijski `agent_reports/` — netaknuti (dodat samo ovaj i plan fajl).

## Not implemented (namjerno)

- Brisanje "Podjela zadataka po fazama" tabele — premještena kao
  označena istorijska referenca, ne obrisana. Brisanje bez potvrde nije
  Implementer-ova jednostrana odluka.
- Bilo kakva izmjena semantike procesa (npr. dodavanje novih koraka,
  mijenjanje ko je Implementer/Reviewer) — ovo je čisto reorganizacija.
- FlowOS orchestration, Tool Router, Context Bundle engine — van scope-a,
  nije potrebno za ovu izmjenu.

## Validation

Provjereno direktno, ne samo pretpostavljeno:

```
test -f za svih 10 referenciranih putanja (docs/*, .agent/*, agent_reports/README.md,
  scripts/coordination.py, .claude/settings.json) → sve postoje

grep provjera: svih 16 procesnih sekcija uklonjenih iz CLAUDE.md potvrđeno
  prisutno u novom docs/dentaland-agentski-razvoj.md (Risk nivoi, Task Contract,
  Ownership manifest, Git izolacija, Obavezna procedura, Reviewer Context Pack,
  Strukturiran verdikt, Konflikt/hijerarhija autoriteta, Scope expansion,
  Verifikacija i DoD, Hijerarhija dokaza, Post-merge Integration Gate,
  Evidence paket, Šta ne graditi odmah, Facts vs Decisions, Fact found)

pytest tests/ -q          → 206 passed (identično prije izmjene)
mypy src/dentaland desktop backend → Success: no issues found in 29 source files
ruff check src/dentaland desktop backend tests → All checks passed
```

### Self-check (migracioni vodič §43)

1. Da li je `CLAUDE.md` kraći nego prije? **DA** (296 → 119 linija, -60%).
2. Da li se ključno pravilo izgubilo tokom razdvajanja? **NE** (provjereno
   grep-om, sve 16 sekcija prisutne).
3. Da li postoje dva izvora istine za isti proces? **NE** — `CLAUDE.md`
   sada eksplicitno upućuje na `docs/dentaland-agentski-razvoj.md` kao
   kanonski, stara kontradiktorna tvrdnja uklonjena.
4. Da li `AGENTS.md` i `CLAUDE.md` sada vode do istih shared pravila?
   **DA**.
5. Da li je trenutna agent availability izvučena iz trajnih pravila?
   **DA — nalaz iz sopstvene provjere**: prvobitno sam doslovno prenio
   Codex-nedostupnost pasus (datum, razlog) u `razvoj.md`, iako ista
   informacija već postoji u `.agent/CURRENT_STATE.md`. Ispravljeno prije
   finalizacije — `razvoj.md` sada ima samo generičko pravilo + pokazivač
   na `CURRENT_STATE.md`.
6. Da li PROJECT_MAP odgovara stvarnom kodu? Van scope-a ove faze
   (nedirano), ostaje tačan iz Faze 1.
7. Da li TASK_ROUTING govori šta NE čitati? Van scope-a (nedirano).
8. Da li istorijski `agent_reports` ostaju netaknuti? **DA**.
9. Da li `coordination.py` workflow ostaje validan? **DA** (nedirano,
   samo referenciran).
10. Da li smo napravili nešto što zahtijeva FlowOS da bi radilo? **NE**.
11. Da li smo napravili novu infrastrukturu bez stvarnog problema? **NE**
    — drift je bio dokazan (konkretni primjeri gore), ne hipotetičan.
12. Može li fresh agent dobiti mali task bez repo-wide istraživanja?
    **DA**, i bolje nego prije (kraći `CLAUDE.md` na startu).

Odgovor na 10 i 11 je NE za oba — po vodičevom pravilu, migracija nije
otišla predaleko.

## Review

PENDING — čeka nezavisan review (Crush ili Pi, MEDIUM risk = 1 reviewer
dovoljan po risk tabeli) prije human approval-a. Ovo je veći, teže
reverzibilan zahvat od Faze 1 (dira `CLAUDE.md`/`AGENTS.md` direktno, ne
samo dodaje fajlove) — namjerno NIJE commitovano/mergovano bez pregleda.

## Integration status

`NOT_MERGED` — čeka review i human approval. Worktree
`Dentaland-worktrees/DENT-AGENT-CONTEXT-002` postoji, spreman za pregled.
