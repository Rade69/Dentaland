# Current State

Last updated: 2026-08-24

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

## Current development focus

**Novi fokus (od 24.8.2026): View/Controller/Services arhitektonski
refaktor** — `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`
(REF-00 do REF-08, plan nezavisno provjeren protiv koda prije starta).
Cilj: `main_window.py` i `booking.py` prestaju biti god-object/monolit,
uvodi se pravi Controller sloj. Implementeri Pi i Crush naizmjenično, oba
reviewera (Codex I Claude) obavezna na svaki task (namjerno skuplje od
standardnog MEDIUM procesa, dogovoreno sa Radovanom), pa human approval.

- **`REF-00`** (LOW/MEDIUM, characterization testovi/sigurnosna mreža) —
  MERGED (`ce8d65a`). Implementer Pi: 19 novih testova, uključujući
  baseline za KRITIČAN nalaz otkriven u review-u plana — `booking.py` i
  `requests.py` definišu DVIJE odvojene `OverlapError` klase istog imena
  (desktop hvata jednu, `backend/main.py` drugu). Oba reviewera PASS
  (`agent_reports/2026-08-24-REF-00-review-codex.md`,
  `.../2026-08-24-REF-00-review-claude.md`) — oba nezavisno reprodukovala
  dokaz (Codex: 3 adversarne mutacije; Claude: dodatna mutacija iz drugog
  ugla — nova javna metoda ne kvari API contract test, potvrđuje da
  granica toleriše rast, ne samo brani od brisanja).
- **`REF-01`** (MEDIUM, centralizacija availability/overlap invarijante) —
  MERGED (`fa53340`). Implementer Crush: nov `src/dentaland/services/availability.py`
  (jedini overlap query, acikličan — `requests.py`/`booking.py` zavise od
  njega, ne obrnuto), `OverlapError` kanonizovana u JEDNU klasu (rješava
  REF-00 nalaz), facade (`_check_overlap`) svedena na čistu delegaciju,
  backward-compat import putanje očuvane za GUI. REF-00 testovi za
  dvije-klase stanje svjesno ažurirani (5 asercija `is not` → `is`,
  pregledano liniju po liniju). Detalji:
  `agent_reports/2026-08-24-REF-01-review-claude.md`.
  **Procesna napomena (presedan za buduće REF taskove):** prvi pokušaj
  Crush-a je bio urađen na grani granatoj PRIJE REF-00 merge-a (grana nije
  sadržavala REF-00 sigurnosnu mrežu) — otkriveno prije review-a, vraćeno
  na sinhronizaciju (`git merge origin/main` + svjesno ažuriranje 5 REF-00
  testova), tek onda review. **Uvijek provjeriti da je zavisni task
  stvarno mergovan u `main` PRIJE početka rada, ne samo da postoji kao
  grana.** Odvojeno: REF-01 je mergovan sa SAMO jednim reviewerom
  (Claude) — Radovan je eksplicitno odobrio preskakanje Codexovog review-a
  za ovaj task (odstupanje od dogovorenog "oba reviewera" pravila za
  cijeli REF paket, njegova odluka, ne podrazumijevano ponašanje za
  REF-02+).
- Raspored ostatka: REF-02 Pi, REF-03 Crush, REF-04 Pi, REF-05 Crush,
  REF-06 Pi, REF-07 Crush, REF-08 Pi (plan sekcija 17) — namjerno
  sekvencijalno, hotspot fajlovi bi inače stvarali merge konflikte.

**Prioritet A i B backloga (`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`) su
kompletno MERGED prije ovog refaktora** (23–24.8.2026) — email-audit
paket (`DENT-022` HIGH, `DENT-023` LOW), `DENT-IMPROVE-007` (backup CLI),
`DENT-IMPROVE-009` (Windows packaging). Detalji istorije: prethodne verzije
ovog fajla u git log-u, ili `agent_reports/` po task ID-u. Vrijedan
presedan iz tog paketa i dalje relevantan: implementer (bilo koji agent)
tvrdi PASS, ali review UVIJEK nezavisno REPRODUKUJE dokaz (živi
build/test/repro), ne samo čita izvještaj — DENT-022 runda 1 je pokazala
da čak i pažljiv implementer može zapisati netačnu tvrdnju, uhvaćeno tek
nezavisnim review-om.

Post-merge integration gate na `main` nakon REF-01: 322 pytest passed,
ruff/mypy čisti (vidi "Current verification baseline" ispod).

Stari worktree-ovi (`DENT-022-reminder-dedup`, `DENT-023-smtp-env-dokumentacija`,
`DENT-IMPROVE-007-backup-cli`, `DENT-IMPROVE-009-windows-packaging`,
`REF-00-characterization-tests`, `REF-01-availability-invariant`) su
ostavljeni netaknuti — ukloniti po potrebi.

**Nema trenutno aktivnog REF taska** — REF-01 je DONE. Sljedeći na redu je
**REF-02 (Pi)** po planu (sekcija 17), zavisnost REF-01 (sad zadovoljena).
Prioritet C (`DENT-IMPROVE-010`..`015`, "prije javnog online bookinga")
čeka da se cijeli refaktor završi (plan sekcija 23 — nema smisla prije
finalnog architecture review-a poslije REF-08).

Novo: `docs/dentaland-komunikacija-agenata.md` — komunikacijska pravila za
agente (pozitivni/negativni obrasci, referentni kodovi F1/D1/R1..., primjeri
iz stvarnih incidenata), uvezano u `AGENTS.md` reading listu. Co-Authored-By
linija u commitovima OSTAJE (Radovanova eksplicitna odluka, 24.8.2026).

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

Izmjereno 2026-08-24 na `main`, post-merge gate nakon REF-01 (merge
`fa53340`):

- `pytest tests/ -q` → **322 passed**, 11 warnings (deprecation
  warnings iz `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog
  koda), ~15-20s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 38
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

Korektivni paket FIX-01..06, Codex-ov FIX-07/08/09, email-audit paket
DENT-022/DENT-023, `DENT-IMPROVE-007`/`009`, REF-00 i REF-01 su svi
zatvoreni (DONE). **Sljedeći na redu: REF-02 (Pi)** — range-based
scheduling reads + eager loading, zavisnost REF-01 (zadovoljena), plan
sekcija 9. Nakon toga: REF-03 Crush, REF-04 Pi, REF-05 Crush, REF-06 Pi,
REF-07 Crush, REF-08 Pi, pa finalni arhitektonski acceptance review
(Codex + Claude, plan sekcija 20) prije nego što ima smisla krenuti na
Prioritet C (`DENT-IMPROVE-010`..`015`, Faza 1 priprema).

Podsjetnik: fizičan clean-machine test za `DENT-IMPROVE-009` (na drugoj
mašini) ostaje Radovanova provjera — implementacija/review su samo
simulirali to lokalno.
