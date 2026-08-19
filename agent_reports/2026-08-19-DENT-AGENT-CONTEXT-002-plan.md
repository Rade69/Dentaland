# Plan prije izmjene — DENT-AGENT-CONTEXT-002 (Faza 2: konsolidacija + thin router)

Risk: MEDIUM (dokumentacija, nema koda, ali dira `CLAUDE.md`/`AGENTS.md` —
globalna pravila koja svaki budući agent čita prvi; greška ovdje utiče na
sve sljedeće taskove). Implementer: Claude. Reviewer 1: Crush ili Pi
(nezavisno od ove sesije). Human approval: Radovan, prije merge-a.

## Cilj

`docs/dentaland-agentski-razvoj.md` postaje kanonski, ažuran procesni
dokument. `CLAUDE.md` postaje thin router (nekoliko KB, ne priručnik).
Ukloniti postojeći drift između ta dva fajla, ne uvesti novi.

## Fact found — drift je stvaran, ne hipotetičan

Pročitao sam sva tri fajla kompletno (296+39+172 linija) prije bilo kakve
izmjene. `docs/dentaland-agentski-razvoj.md` je zastario u odnosu na
`CLAUDE.md` na nekoliko konkretnih mjesta:

- Koristi binarni "kritičan da/ne" umjesto LOW/MEDIUM/HIGH — `CLAUDE.md`
  eksplicitno kaže da ovaj sistem "zamjenjuje" stari.
- "Reviewer 2: Codex" fiksno — `CLAUDE.md` ima ažurnu tabelu uloga
  (Crush/Pi kao Implementer na LOW/MEDIUM, Claude na HIGH, Codex
  privremeno nedostupan od 18.8.2026).
- "Podjela zadataka po fazama" tabela (0.1–M1.3 numeracija) — provjereno
  `grep` kroz `agent_reports/*.md`: **0 pogodaka** za tu numeraciju, **48**
  fajlova koristi `DENT-XXX`. Tabela je napuštena u praksi, ne aktivan
  izvor istine.
- Hijerarhija autoriteta — sličan ali ne identičan redoslijed/sadržaj u
  odnosu na `CLAUDE.md` verziju (npr. `docs/` izvori istine nedostaju kao
  eksplicitna stavka).

## Pogođeno

- `docs/dentaland-agentski-razvoj.md` — postaje kanonski, prima ažuran
  sadržaj iz `CLAUDE.md` (risk tabela, uloge, Task Contract format,
  ownership/coordination, Reviewer Context Pack, strukturiran verdikt,
  OUT_OF_SCOPE_FINDING, Post-merge Integration Gate, hijerarhija
  autoriteta, PROBE/Facts-vs-Decisions gdje relevantno).
- `CLAUDE.md` — smanjuje se na: projektne premise (šta je Dentaland, jezik,
  klijent/razmjer, arhitektura, šta se ne gradi, sigurnost/privatnost —
  ovo je SADRŽAJ specifičan za Dentaland, ne proces, i ostaje ovdje jer
  nije "kako se radi" nego "šta je projekat"), thin router na vrhu
  (`.agent/PROJECT_MAP.md`, `.agent/TASK_ROUTING.md`, Task Contract), i
  pokazivač na `docs/dentaland-agentski-razvoj.md` za pun proces.
- `AGENTS.md` — početna instrukcija se ažurira sa "pročitaj CLAUDE.md u
  cijelosti" na kraću navigaciju kroz thin router + `.agent/` (isti
  princip kao Faza 1, ali sada je i sâm CLAUDE.md kraći, pa je i AGENTS.md
  poziv na njega tačniji).

## Šta NE dirati

- Semantiku BILO KOJEG pravila — ovo je premještanje/deduplikacija, ne
  redizajn procesa. Ako se sadržaj razlikuje između CLAUDE.md i razvoj.md,
  pobjeđuje CLAUDE.md verzija (novija, po njegovoj vlastitoj tvrdnji u
  "Izvori istine" sekciji), ne moja procjena šta je "bolje".
- `docs/dentaland-razvojni-plan.md`, `docs/dentaland-razvojni-plan-v3.1.md`
  — arhitektura/tehnički sadržaj, van scope-a ove konsolidacije.
- Sigurnosne/privacy stavke u trenutnom `CLAUDE.md` (sekcija "Sigurnost i
  privatnost") — ovo je projektni sadržaj (šta MORA biti tačno o
  Dentalandu), ne proces (kako se radi) — ostaje u `CLAUDE.md`, ne seli se.
- "Podjela zadataka po fazama" tabela — NEĆE biti obrisana bez odluke;
  premjestiće se kao jasno označen istorijski/referentni dodatak na dnu
  `docs/dentaland-agentski-razvoj.md` (dokazano napuštena u praksi, ali
  brisanje istorijskog konteksta nije ovlaštenje koje imam bez pitanja —
  ako se pokaže da nema vrijednosti ni kao referenca, to je pitanje za
  Radovana, ne moja jednostrana odluka).
- `.agent/` sloj (Faza 1) — ne dirati sadržajno, samo referencirati.

## Plan (redoslijed)

1. Prepisati `docs/dentaland-agentski-razvoj.md`: zamijeniti zastarjele
   sekcije (Uloge, risk klasifikacija, hijerarhija autoriteta) ažurnim
   sadržajem iz `CLAUDE.md`; dodati sekcije koje `CLAUDE.md` ima a
   razvoj.md nema (Task Contract format sa `allowed_paths`/
   `forbidden_paths`, ownership/coordination preko `scripts/
   coordination.py`, Facts vs Decisions format); premjestiti "Podjela
   zadataka po fazama" na dno kao označen istorijski dodatak.
2. Prepisati `CLAUDE.md`: zadržati projektni sadržaj (šta je Dentaland,
   jezik, arhitektura, šta se ne gradi, sigurnost/privatnost, otvorena
   pitanja); zamijeniti procesne sekcije kratkim pokazivačem na
   `docs/dentaland-agentski-razvoj.md`; dodati "Start here" navigaciju na
   vrh (`AGENTS.md` → `.agent/PROJECT_MAP.md` → Task Contract →
   `.agent/TASK_ROUTING.md`).
3. Ažurirati `AGENTS.md` početnu instrukciju.
4. Provjeriti da svaki interni link (`docs/...`, `.agent/...`) stvarno
   postoji (`test -f`), ne pretpostaviti.

## Plan verifikacije

- Svaki fajl/putanja spomenuta u novim verzijama fajlova stvarno postoji
  (`test -f` za svaku).
- `git diff` pregled — potvrditi da nijedno pravilo nije tiho izgubljeno
  (uporediti sadržajno staru i novu verziju, ne samo dužinu).
- `pytest tests/ -q`, `ruff check`, `mypy` — potvrditi da dokumentacija
  ne dira kod (očekivano: identičan rezultat kao prije, 206/206, 0 mypy
  grešaka).
- Self-check pitanja iz migration vodiča (§43): da li je CLAUDE.md kraći,
  da li je pravilo izgubljeno, da li postoje dva izvora istine za isti
  proces, da li AGENTS.md i CLAUDE.md vode do istih shared pravila.

## Rollback/oporavak

Sve u odvojenom worktree-u (`task/DENT-AGENT-CONTEXT-002`), ništa
commitovano dok se ne potvrdi. Ako se pokaže da je nešto izgubljeno,
worktree se briše bez posljedica po `main`.

## Odbačene opcije

| Opcija | Zašto razmatrana | Zašto odbačena | Kad ponovo otvoriti |
|---|---|---|---|
| Obrisati "Podjela zadataka po fazama" tabelu potpuno | Dokazano napuštena u praksi (0 referenci u 48 DENT-XXX taskova) | Brisanje istorijskog konteksta bez potvrde nije Implementer-ova jednostrana odluka | Ako Radovan potvrdi da nema vrijednosti ni kao referenca |
| Izbrisati `docs/dentaland-agentski-razvoj.md` i sve prebaciti u CLAUDE.md | Jednostavnije, jedan fajl | Suprotno cilju Faze 2 (CLAUDE.md treba biti THIN, ne rasti) i suprotno vodiču koji Fazu 2 eksplicitno traži | Ne — suprotno cilju zadatka |
