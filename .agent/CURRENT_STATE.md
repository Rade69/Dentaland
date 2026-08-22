# Current State

Last updated: 2026-08-21

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

`FIX-02` (LOW), `FIX-01`, `FIX-03`, `FIX-04` i `FIX-05` (sve MEDIUM osim
FIX-02) su svi MERGED → INTEGRATION_VERIFIED → DONE (merge `ae6e52f`,
`9808475`, `53db57c`, `a6cdc2a`, `8576408`, 21.8.2026). Implementer svih
pet puta Pi, review Claude PASS. FIX-05 napomena: implementer je ovaj
put SAM commitovao rad prije traženja odobrenja (odstupanje od
dosadašnjeg "nikad commit bez eksplicitnog zahtjeva" obrasca) — bez
štete, ali vrijedi pratiti da li se ponavlja. FIX-03 je trebao **tri
runde** review-a — vrijedi zapamtiti kao presedan:
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
redoslijed FIX-02 → FIX-01 → 03 → 04 → 05 → 06): **FIX-06** (vizuelno
usklađivanje Settings/Blockout, LOW) — posljednji u paketu. Task
Contract spreman (`agent_reports/FIX-06-task-contract.md`): (A)
`ServiceDialog`/`IntervalDialog` u `settings_panel.py` prelaze sa
`QDialog`+`QDialogButtonBox` na `BaseDialog` (poziv-ugovor prema
`SettingsPanel` nepromijenjen — `exec()`/`values()` isti); (B)
`blockout_panel.py`-ova `QMessageBox.question` potvrda brisanja
zamijenjena Dentaland destructive-confirm dijalogom po uzoru na
`delete_appointment.py` (BEZ Enter-safety izuzetka — taj je specifičan
samo za hard-delete termina). Dodijeljeno Pi-ju.

**Paralelno, van ovog korektivnog paketa (Codex, ne moj task):**
`DENT-021` (panel doktora sa fotografijama) je MERGED (`9f08a7e`,
21.8.2026). Vrijedi zapamtiti: Pi-jevi placeholder PNG-ovi su prije
merge-a zamijenjeni Codex-ovim originalnim realističkim fotografijama —
kod Pi-jev, slikovni asseti Codex-ovi.

`FIX-07` (WeekView kartica odsječena na donjoj granici prikaza, LOW,
`agent_reports/FIX-07-task-contract.md`) — Codex trenutno radi DIREKTNO
u glavnom checkout-u (ne worktree, isti obrazac kao DENT-021), stanje
21.8.2026 necommitovano. `python scripts/coordination.py status`
pokazuje aktivan claim na `week_view.py`/`test_week_view.py`. Provjeriti
claim status prije bilo kakvog rada na tim fajlovima.

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

Izmjereno 2026-08-21 na `main`, post-merge gate nakon `FIX-05` (broj
uključuje Codex-ov paralelni necommitovan `FIX-07` rad prisutan u
checkout-u u trenutku mjerenja — izolovan FIX-05-samo test u worktree-u
prije merge-a bio je 276):

- `pytest tests/ -q` → **277 passed**, 11 warnings (deprecation warnings iz
  `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda), ~11s.
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

`FIX-06` čeka implementaciju (Pi, vidi "Current development focus") —
posljednji u korektivnom paketu. Nakon toga Prioritet B backloga
(`DENT-IMPROVE-007`/`009`).
