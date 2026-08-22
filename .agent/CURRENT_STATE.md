# Current State

Last updated: 2026-08-21

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

**Korektivni paket FIX-01 do FIX-06 je KOMPLETAN** — svih šest je
MERGED → INTEGRATION_VERIFIED → DONE (merge `ae6e52f`, `9808475`,
`53db57c`, `a6cdc2a`, `8576408`, `fca60f8`, 21.8.2026). Implementer svih
šest puta Pi, review Claude PASS. FIX-05/06 napomena: implementer je
oba puta SAM commitovao rad prije traženja odobrenja (odstupanje od
ranijeg "nikad commit bez eksplicitnog zahtjeva" obrasca iz FIX-01..04)
— bez štete, ali vrijedi pratiti kao noviji ustaljen obrazac, ne
tretirati kao anomaliju. FIX-03 je trebao **tri runde** review-a —
vrijedi zapamtiti kao presedan:
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

Cijeli glavni scheduler workflow (appointment editor, detalji, cancel,
delete, move, status akcije, DayView blockout+drag&drop, status
semantika, Settings, Blockout) je sada vizuelno i funkcionalno
dosljedan — nema više poznatih otvorenih stavki iz
`docs/dentaland-desktop-korektivni-plan.md`.

**Paralelno, van ovog korektivnog paketa (Codex, ne moj task):**
`DENT-021` (panel doktora sa fotografijama) je MERGED (`9f08a7e`,
21.8.2026). Vrijedi zapamtiti: Pi-jevi placeholder PNG-ovi su prije
merge-a zamijenjeni Codex-ovim originalnim realističkim fotografijama —
kod Pi-jev, slikovni asseti Codex-ovi.

`FIX-07` (WeekView kartica odsječena na donjoj granici prikaza, LOW,
`agent_reports/FIX-07-task-contract.md`) — Codex je commitovao direktno
na `main` (`4f47565`, 21.8.2026), rađeno direktno u glavnom checkout-u
(ne worktree, isti obrazac kao DENT-021). **Nije prošlo kroz Claude
nezavisan review niti human approval koliko je poznato** — commitovano
mimo Task Contract review toka. Vrijedi provjeriti sa Radovanom da li je
to namjerno prihvaćeno ili treba naknadni review. Untracked
`.tmp-pytest-fix08/` u checkout-u nagovještava da Codex možda već radi
i na FIX-08 — nema još task contracta za to, provjeriti
`coordination.py status` uživo prije pretpostavke.

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

Izmjereno 2026-08-21 na `main`, post-merge gate nakon `FIX-06` (broj
uključuje Codex-ov paralelni necommitovan `FIX-07` rad prisutan u
checkout-u u trenutku mjerenja — izolovan FIX-06-samo test u worktree-u
prije merge-a bio je 284):

- `pytest tests/ -q` → **285 passed**, 11 warnings (deprecation warnings iz
  `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda), ~10s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 36
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

Korektivni paket FIX-01..06 je zatvoren. Sljedeći prioritet po
`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`: **Prioritet B** —
`DENT-IMPROVE-007` (operativni automatski backup) ili
`DENT-IMPROVE-009` (Windows packaging), Radovanova odluka koji prvo.
(`FIX-07`/eventualni `FIX-08` su Codex-ov paralelan rad, ne dio ovog
plana — vidi "Current development focus".)
