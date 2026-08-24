# AGENTS.md — Dentaland

Ovo je Dentaland — sistem zakazivanja za stomatološku ordinaciju, građen za Ljubu (vidi `CLAUDE.md`).

## Izvor istine

`CLAUDE.md` u korijenu ovog repoa je **operativni izvor istine za SVE agente** (Claude, Codex, Crush, Pi), ne samo za Claude Code — ime fajla je istorijska posljedica toga koji je alat prvi uveo tu konvenciju, ne ograničenje ko ga poštuje. Prije bilo kakvog rada na ovom repou:

1. Pročitaj `CLAUDE.md` (thin router — projektne premise i navigacija, ne cijeli proces).
2. Pročitaj `.agent/PROJECT_MAP.md` — gdje se šta nalazi.
3. Pročitaj konkretan Task Contract za zadatak.
4. Koristi `.agent/TASK_ROUTING.md` za dodatni kontekst po tipu zadatka.
5. Za pun proces (risk nivoi, Task Contract format, ko je
   Implementer/Reviewer, review verdikt) — `docs/dentaland-agentski-razvoj.md`,
   ne `CLAUDE.md` direktno.
6. Za stil komunikacije (kako pisati u chatu i u `agent_reports/**`, ne
   šta raditi) — `docs/dentaland-komunikacija-agenata.md`.

Ne dupliramo taj sadržaj ovdje — jedan izvor istine, da se pravila ne raziđu kad se izvorni dokument ažurira.

## Koordinacija više agenata — obavezan korak prije paralelnog rada

Kad radiš na zadatku dok drugi agent (Claude/Codex/Crush/Pi) možda paralelno radi na drugom zadatku u drugom git worktree-u, koristi `scripts/coordination.py` da spriječiš da dva agenta nezavisno mijenjaju iste fajlove:

```bash
# Na početku zadatka — iz svog worktree-a, prijavi koje fajlove diraš
python scripts/coordination.py claim --task DENT-014 --agent codex --paths backend/services/tokens.py,tests/test_tokens.py

# --agent je jedno od: claude | codex | crush | pi

# Provjeri ko trenutno šta drži
python scripts/coordination.py status

# Prije nego dirneš fajl koji nisi ti zauzeo (opciono, ali preporučeno ako nisi siguran)
python scripts/coordination.py check --path backend/services/tokens.py

# Na kraju zadatka — obavezno oslobodi
python scripts/coordination.py release --task DENT-014
```

Ako `claim` javi konflikt (exit code 1, ispisuje koja putanja je već zauzeta i od koga), **ne pregazi to** — sačekaj da drugi zadatak oslobodi putanju, ili koordiniraj sa Radovanom/Ljubom oko redoslijeda.

Registar (`.coordination/registry.db`) je lokalan, dijeljen preko svih worktree-ova istog repoa, i gitignored — nije trajna evidencija, samo runtime koordinacija dok su zadaci aktivni.

**Claude Code** ima ovo dodatno automatizovano kroz `PreToolUse` hook (`.claude/settings.json`) — Edit/Write se automatski blokira ako pokušaš dirnuti tuđ aktivan claim, bez potrebe da ručno zoveš `check`. Codex, Crush i Pi trenutno nemaju taj automatski hook ožičen iz ove sesije (nepoznato je da li i kako ti alati podržavaju pre-edit hookove) — zato je `claim`/`release` disciplina za njih ručna, ne automatska.

Dok postoji samo jedan aktivan zadatak na repou, `claim`/`release` nije obavezan (nema s kim se sudariti), ali se preporučuje radi navike.

**`agent_reports/` je dijeljen folder — ne claimuj ga u cjelini.** Svaki zadatak piše svoj različito imenovan fajl (`DENT-XXX-*.md`) tamo, pa nema stvarnog rizika preklapanja. Ako dva zadatka oba pozovu `claim --paths ...,agent_reports`, alatka će ih tretirati kao koliziju iako fizički ne postoji — claimuj konkretan fajl (`agent_reports/DENT-003-task-contract.md`), ne cijeli folder.
