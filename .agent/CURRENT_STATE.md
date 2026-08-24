# Current State

Last updated: 2026-08-23

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

**Email obavještenja su uživo testirane i potvrđene da rade** (23.8.2026,
Radovan, pravi Gmail SMTP) — oba trenutna tipa (zahtjev primljen, termin
potvrđen) stigla su u inbox tačnog sadržaja. Dvije poznate praznine iz tog
audita su sad **obje MERGED u `main` i DONE** (24.8.2026):

- **`DENT-022`** (HIGH, zaštita od dupliranog slanja podsjetnika —
  aditivna kolona `Appointment.reminder_sent_at`) — MERGED, merge commit
  `768706e`. Post-merge integration gate na `main`: 289 pytest passed,
  ruff/mypy čisti. Tok koji vrijedi zapamtiti:
  - Runda 1 (commit `770452d`): Codex Reviewer 1 **REJECT** — dokazan
    pravi paralelni race (`CONCURRENT_SEND_COUNT 2`). Implementerov
    (Claude) vlastiti adversarni claim u izvještaju runde 1 je bio
    **faktički netačan** — uhvaćeno Codexovim review-om, ne prije.
  - Runda 2 (fix, commit `e479446`): "zauzmi pa pošalji" — atomski
    `UPDATE ... WHERE reminder_sent_at IS NULL` + `rowcount` prije SMTP
    poziva. Pi review PASS kao Reviewer 2 (izvorno pogrešno označen kao
    Reviewer 1 — Codex je obavezan Reviewer 1 na HIGH kad je dostupan;
    ispravljeno, sadržaj nedirnut). Codex Reviewer 1 runde 2 **PASS_WITH_NOTES**
    (`agent_reports/2026-08-24-DENT-022-review-codex-round2.md`) — oba
    blocking nalaza iz runde 1 nezavisno potvrđena zatvorena (30/30
    živih konkurentnih repro rundi).
  - **Prihvaćen kompromis (Radovan eksplicitno odobrio prije merge-a)**:
    sistem sad garantuje **at-most-once, ne exactly-once** — ako proces
    crash-uje NAKON uspješnog commit-a markera a PRIJE SMTP poziva,
    taj podsjetnik je trajno propušten (marker ostaje postavljen, ne
    pokušava se ponovo). Nužna cijena za sprečavanje duplog slanja bez
    outbox/idempotency mehanizma — svjesno odstupanje od originalnog
    Task Contracta, ne previd.
- **`DENT-023`** (LOW, `.env.example` + README SMTP dokumentacija) —
  MERGED, merge commit `3eef6e4`. Implementacija Pi (`795aa12`), review
  Claude PASS.

Worktree-ovi `DENT-022-reminder-dedup` i `DENT-023-smtp-env-dokumentacija`
su ostavljeni netaknuti (nisu obrisani) — ukloniti ih po potrebi.

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

`FIX-07` (WeekView kartica odsječena na donjoj granici, LOW), `FIX-08`
(avatari doktora 48→56px, LOW) i `FIX-09` (redizajn "Novi zahtjevi"
stranice, LOW) su sada svi MERGED → INTEGRATION_VERIFIED → DONE (merge
`4f47565`, `18f264a`+`5fac891`, `7f1386f`+`6b3196c`, 21–22.8.2026), svi
pušovani. Codex je sve implementirao van Task Contract review toka
(FIX-07 direktno u glavnom checkout-u kao DENT-021; FIX-08/09 u
worktree-ovima, ali FIX-08 lokalno mergovan bez pushovanja dok Claude
nije provjerio). Codex-ov vlastiti "independent-codex"/"independent"
review nije stvaran nezavisan review. Radovan je tražio naknadnu
provjeru ("Provjeri ovo što je Codex radio") — Claude je uradio pravi
nezavisan review za sva tri, adversarno potvrđena PASS (vidi
`agent_reports/2026-08-22-FIX-07-review-claude.md`,
`.../2026-08-22-FIX-08-review-claude.md`,
`.../2026-08-22-FIX-09-review-claude.md`), Radovan je potom dao human
approval za sve. FIX-09 review je uključivao stvaran klik na "Obradi"
dugme do stvarnog upisa u bazu (ne samo testove) i pogodio isti poznat
`QDialog.exec()` monkeypatch-hang gotcha (vidi taj review za detalje
kako je bezbjedno riješeno — samo ciljani PID, ne blanket taskkill). Kod
je ispravan za sve; otvoreno pitanje je SAMO proces (treći+ put da
Codex zaobiđe review/worktree-izolaciju) — vrijedi razgovarati sa
Radovanom o tome treba li nešto promijeniti u Codex-ovom usmjeravanju.

Prioritet A backloga (`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`,
`DENT-IMPROVE-001` do `006`) je MERGED — vidi "Recently completed major
work" ispod. Prioritet B (`007` backup, `009` Windows packaging) čeka
poslije korektivnog paketa.

**Email live test je ZAVRŠEN uspješno (23.8.2026)** — vidi prvi odjeljak
iznad. Obje poznate praznine iz tog audita (dedup zaštita, SMTP env var
dokumentacija) su u toku/gotove kao `DENT-022`/`DENT-023` iznad. Radovanov
`dev_local.py` je možda i dalje aktivan u zasebnom terminalu iz tog
testiranja — provjeriti prije pretpostavke da nije, prije nego što se
sam pokreće drugi backend/web server na istim portovima.

## Agent availability

**Codex ponovo dostupan (od 19.8.2026).** Privremena nedostupnost
(18.8.2026, isticanje kredita) je gotova — uloge se vraćaju na standardnu
raspodjelu: Codex opciono na LOW/MEDIUM implementaciji, obavezan Reviewer 1
na HIGH (uz Crush ili Pi kao Reviewer 2), po tabeli uloga u
`docs/dentaland-agentski-razvoj.md` — kanonski procesni dokument nakon
Faze 2 merge-a (`DENT-AGENT-CONTEXT-002`, MERGED 20.8.2026, tri Codex
review runde). `CLAUDE.md` je sada thin router, ne sadrži tabelu uloga.

## Current verification baseline

Izmjereno 2026-08-24 na `main`, post-merge gate nakon `DENT-022`+`DENT-023`
(merge `768706e`, `3eef6e4`):

- `pytest tests/ -q` → **289 passed**, 11 warnings (deprecation
  warnings iz `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog
  koda), ~15-20s.
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

Korektivni paket FIX-01..06, Codex-ov FIX-07/08/09, i email-audit paket
DENT-022/DENT-023 su svi zatvoreni (mergovani, pušovani, DONE). Nema
trenutno aktivnog HIGH/MEDIUM taska. Sljedeći prioritet po
`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`: **Prioritet B** —
`DENT-IMPROVE-007` (operativni automatski backup) ili
`DENT-IMPROVE-009` (Windows packaging), Radovanova odluka koji prvo.
