# AGENTS.md — Dentaland

Ovo je Dentaland — sistem zakazivanja za stomatološku ordinaciju, građen za Ljubu (vidi `CLAUDE.md`).

## Izvor istine

`CLAUDE.md` u korijenu ovog repoa je **operativni izvor istine za SVE agente** (Claude, Codex, Crush), ne samo za Claude Code — ime fajla je istorijska posljedica toga koji je alat prvi uveo tu konvenciju, ne ograničenje ko ga poštuje. Prije bilo kakvog rada na ovom repou, pročitati `CLAUDE.md` u cijelosti: risk nivoi (LOW/MEDIUM/HIGH), Task Contract format, git izolacija (worktree po zadatku), obavezna procedura prije izmjene, ko je Implementer/Reviewer, i pravila sigurnosti/privatnosti specifična za projekat.

Ne dupliramo taj sadržaj ovdje — jedan izvor istine, da se pravila ne raziđu kad se CLAUDE.md ažurira.

## Koordinacija više agenata — obavezan korak prije paralelnog rada

Kad radiš na zadatku dok drugi agent (Claude/Codex/Crush) možda paralelno radi na drugom zadatku u drugom git worktree-u, koristi `scripts/coordination.py` da spriječiš da dva agenta nezavisno mijenjaju iste fajlove:

```bash
# Na početku zadatka — iz svog worktree-a, prijavi koje fajlove diraš
python scripts/coordination.py claim --task DENT-014 --agent codex --paths backend/services/tokens.py,tests/test_tokens.py

# --agent je jedno od: claude | codex | crush

# Provjeri ko trenutno šta drži
python scripts/coordination.py status

# Prije nego dirneš fajl koji nisi ti zauzeo (opciono, ali preporučeno ako nisi siguran)
python scripts/coordination.py check --path backend/services/tokens.py

# Na kraju zadatka — obavezno oslobodi
python scripts/coordination.py release --task DENT-014
```

Ako `claim` javi konflikt (exit code 1, ispisuje koja putanja je već zauzeta i od koga), **ne pregazi to** — sačekaj da drugi zadatak oslobodi putanju, ili koordiniraj sa Radovanom/Ljubom oko redoslijeda.

Registar (`.coordination/registry.db`) je lokalan, dijeljen preko svih worktree-ova istog repoa, i gitignored — nije trajna evidencija, samo runtime koordinacija dok su zadaci aktivni.

**Claude Code** ima ovo dodatno automatizovano kroz `PreToolUse` hook (`.claude/settings.json`) — Edit/Write se automatski blokira ako pokušaš dirnuti tuđ aktivan claim, bez potrebe da ručno zoveš `check`. Codex i Crush trenutno nemaju taj automatski hook ožičen iz ove sesije (nepoznato je da li i kako ti alati podržavaju pre-edit hookove) — zato je `claim`/`release` disciplina za njih ručna, ne automatska.

Dok postoji samo jedan aktivan zadatak na repou, `claim`/`release` nije obavezan (nema s kim se sudariti), ali se preporučuje radi navike.
