# Current State

Last updated: 2026-08-21

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

`FIX-02` (LOW), `FIX-01` (MEDIUM) i `FIX-03` (MEDIUM, razdvajanje
NO_SHOW/CANCELLED) su svi MERGED → INTEGRATION_VERIFIED → DONE (merge
`ae6e52f`, `9808475`, `53db57c`, 21.8.2026). Implementer sva tri puta
Pi, review Claude PASS. FIX-03 je trebao **tri runde** review-a — vrijedi
zapamtiti kao presedan:
1. Implementacija PASS na logici statusa, ali status legenda (6 stavki
   umjesto 5) vizuelno pretjecala kontejner na 1536×760 (385px
   odsijecanja) — REJECT.
2. Popravka (manji font/spacing) je bila ispravna, ALI dodati
   regresioni test (`.width()` vs `.sizeHint().width()` geometrijsko
   poređenje) je davao **lažan PASS na buggy kodu** — pytest-qt/offscreen
   layout timing čini geometrijska poređenja nepouzdanim za ovakve
   provjere. REJECT po drugi put.
3. Test zamijenjen determinističkom provjerom generisanog HTML sadržaja
   (npr. `assert "font-size:10px" in html`) — adversarno potvrđeno da
   stvarno pada na buggy kodu. PASS.

**Pouka za buduće taskove koji provjeravaju layout/veličinu u GUI
testovima**: ne oslanjati se na `.width()`/`.sizeHint()` poređenja u
pytest-qt offscreen okruženju bez adversarne provjere (namjerno vratiti
buggy kod i potvrditi da test PADA) — ovakva geometrijska poređenja
mogu davati lažan PASS.

Sljedeći u korektivnom paketu (`docs/dentaland-desktop-korektivni-plan.md`,
redoslijed FIX-02 → FIX-01 → 03 → 04 → 05 → 06): **FIX-04** (tiho
gutanje `ValueError` grešaka bez feedbacka, LOW/MEDIUM) — priprema u
toku.

**Paralelno, van ovog korektivnog paketa:** `DENT-021` (panel doktora sa
fotografijama u desnoj koloni) je MERGED → INTEGRATION_VERIFIED → DONE
(merge `9f08a7e`, 21.8.2026). Prošao kroz reviziju — Codex-ova prva
necommitovana verzija (rađena direktno u glavnom checkout-u, proceduralno
odstupanje, zabilježeno ali bez štete) je imala premale avatare (38px) i
prazan indikator boje bez broja; Radovan je tražio veće fotografije
(48px) i brojčanu znaku (broj termina po doktoru u trenutnom periodu,
nezavisno od doctor-filter taba). Pi je implementirao reviziju fresh u
worktree-u; Claude review PASS (adversarno potvrđeno — avatar veličina
mjerena direktno, filter-nezavisnost dokazana preko `set_filter`).
Finalna napomena: Pi-jevi placeholder PNG-ovi (generisani, ~370 bajtova)
zamijenjeni Codex-ovim originalnim realističkim fotografijama tokom
finalne provjere prije merge-a — kod je Pi-jev, slikovni asseti su
Codex-ovi. `main_window.py`/`test_main_window.py` claim je oslobođen.

Prioritet A backloga (`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`,
`DENT-IMPROVE-001` do `006`) je MERGED — vidi "Recently completed major
work" ispod. Prioritet B (`007` backup, `009` Windows packaging) čeka
poslije korektivnog paketa.

## Agent availability

**Codex ponovo dostupan (od 19.8.2026).** Privremena nedostupnost
(18.8.2026, isticanje kredita) je gotova — uloge se vraćaju na standardnu
raspodjelu: Codex opciono na LOW/MEDIUM implementaciji, obavezan Reviewer 1
na HIGH (uz Crush ili Pi kao Reviewer 2), po tabeli uloga u
`docs/dentaland-agentski-razvoj.md` — kanonski procesni dokument nakon
Faze 2 merge-a (`DENT-AGENT-CONTEXT-002`, MERGED 20.8.2026, tri Codex
review runde). `CLAUDE.md` je sada thin router, ne sadrži tabelu uloga.

## Current verification baseline

Izmjereno 2026-08-21 na `main`, post-merge gate nakon `FIX-03`:

- `pytest tests/ -q` → **269 passed**, 11 warnings (deprecation warnings iz
  `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda), ~10s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 35
  source files.**

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

## Next known work

`FIX-04` (tiho gutanje `ValueError` grešaka, LOW/MEDIUM — vidi
`docs/dentaland-desktop-korektivni-plan.md` sekcija 5) — priprema u
toku. Nakon toga FIX-05/06. Prioritet B backloga
(`DENT-IMPROVE-007`/`009`) čeka poslije cijelog korektivnog paketa.
