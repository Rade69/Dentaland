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

- **`REF-00`** (characterization testovi) — MERGED (`ce8d65a`). Baseline
  za KRITIČAN nalaz — dvije odvojene `OverlapError` klase istog imena.
- **`REF-01`** (centralizacija availability/overlap invarijante) — MERGED
  (`fa53340`). `OverlapError` kanonizovana u JEDNU klasu. Procesni
  presedan: uvijek provjeriti da je zavisni task STVARNO mergovan u
  `main` prije početka rada, ne samo da postoji kao grana.
- **`REF-02`** (range-based reads + eager loading) — MERGED (`d4b09e7`).
  Presedan: Codex REJECT→PASS o kvalitetu testova, ne arhitekturi.
- **`REF-03`** (razbijanje `booking.py`) — MERGED (`a02f31f`). Najveći
  servisni task. **Najvredniji procesni presedan cijelog paketa:**
  arhitektonski test je prošao TRI Codex REJECT runde — Radovan je
  naredio da Codex sam završi fix, čime Codex više nije bio nezavisan
  reviewer za taj dio; **Pi je preuzet kao FRESH Reviewer 1**.
- **`REF-04`** (Controller sloj za appointment workflow) — MERGED
  (`3e0a0c2`). PRVI task koji dira `desktop/` — `AppointmentController`.
- **`REF-05`** (`ScheduleController` + refresh orchestration) — MERGED
  (`a422c40`). Presedan sličan REF-02: Codex REJECT runda 1 (query-counter
  test koristio fake view, ne prave klase) → integracijski testovi sa
  pravim view objektima → Codex PASS runda 2.
- **`REF-06`** (shared presentation logika iz WeekView/DayView) — MERGED
  (`858b836`). Nov `desktop/presentation/` (`schedule_status.py`,
  `schedule_palette.py`) — jedina istina za status/paletu; `day_view.py`
  više ne uvozi ništa iz `week_view.py`. Backward-compat re-export u
  `week_view.py` (za `main_window.py`/`dialogs/**`, forbidden paths za
  ovaj task) — Codex adversarno dokazao da re-export ima stvarne
  potrošače, nije mrtav kod. Pronađen i prijavljen TREĆI privatni simbol
  (`WeekView._DOCTOR_PALETTE`, korišćen u `main_window.py:313`) kao
  `OUT_OF_SCOPE_FINDING` — Pi ga NIJE tiho popravio van scope-a, dobar
  primjer discipline.
- **`REF-07`** (Request i Print controller granice) — MERGED (`f541e0a`).
  `RequestController`/`PrintController` (novo) preuzeli `process_pending_request`
  iz `requests_panel.py` i print workflow iz `MainWindow`-a. **Pozitivan
  kontraprimer za tehnički dug ispod:** `PrintController` prima
  `week_start_provider: Callable[[], date]` kroz konstruktor — čist DI
  bez "gledanja nazad" u konkretnu klasu, rješava isti tip problema kao
  REF-04/05 kompromisi ali na čistiji način. Vrijedi kao model za REF-08.

  **Zbirni tehnički dug — Controller "gleda nazad" u View, TRI mjesta
  kroz REF-04+REF-05 (jedan zbirni zapis, ne razdvojeno):**
  1. (REF-04) `AppointmentController` lazy-uvozi Dialog klase iz
     `desktop.views.main_window` unutar metoda — jer GUI testovi
     monkeypatch-uju dijaloge NA main_window modulu POSLIJE konstrukcije
     `MainWindow`-a.
  2. (REF-04) `AppointmentController` čita `MainWindow` privatno stanje
     (`_doctors`, `_has_doctors`, `_current_doctor_id`) preko `getattr`.
  3. (REF-05) `ScheduleController` drži SVOJU kopiju `_current_doctor_id`
     — TRI mjesta drže "isti" podatak, sinhronizovana kroz JEDNU
     disciplinovanu UI putanju (`_on_tab_changed`) — nije bug SADA, ali
     svaki BUDUĆI način promjene doktora mora ažurirati sve tri lokacije.
  Svi namjerni, dokumentovani. **REF-08 (završni cleanup) treba svjesno
  razmotriti čišći pristup** — REF-07-ov `week_start_provider` callable
  DI je konkretan, dokazan model kako to izgleda u praksi.
- Raspored ostatka: **REF-08 (Pi)** je zadnji task u paketu (plan sekcija
  15), pa finalni arhitektonski acceptance review (Codex + Claude, plan
  sekcija 20).

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

Post-merge integration gate na `main` nakon REF-06+REF-07: 355 pytest
passed, ruff/mypy čisti (vidi "Current verification baseline" ispod).

Stari worktree-ovi (`DENT-022-reminder-dedup`, `DENT-023-smtp-env-dokumentacija`,
`DENT-IMPROVE-007-backup-cli`, `DENT-IMPROVE-009-windows-packaging`,
`REF-00-characterization-tests`, `REF-01-availability-invariant`,
`REF-02-range-reads`, `REF-03-booking-split`, `REF-04-appointment-controller`,
`REF-05-schedule-controller`, `REF-06-presentation-split`,
`REF-07-request-print-controllers`) su ostavljeni netaknuti — ukloniti po
potrebi.

**Procesni presedan — prvi PARALELAN par REF taskova:** REF-06 (Pi) i
REF-07 (Crush) su rađeni ISTOVREMENO u zasebnim worktree-ovima, pošto
zavisnosti nisu bile ukrštene (REF-06 zavisi od REF-05, REF-07 od REF-04
— ne jedan od drugog) i fajlovi se nisu preklapali. Oba su prošla
`coordination.py claim` bez konflikta, oba review-ovana i mergovana
uzastopno (REF-06 pa REF-07) bez merge konflikta. Dokazuje da paralelni
rad ima smisla KAD se zavisnosti/fajlovi eksplicitno provjere prije
starta — ne default pretpostavka za buduće parove.

**Nema trenutno aktivnog REF taska** — REF-06 i REF-07 su DONE. Sljedeći
na redu je **REF-08 (Pi)** po planu (sekcija 15) — zadnji task u paketu:
theme/QSS izdvajanje iz `main_window.py`, ukloniti `desktop.fake_data`
zavisnost iz produkcijskog View koda (timezone konstanta u
`src/dentaland/timezone.py`), provjeriti PyInstaller build i dalje radi.
Nakon REF-08: **finalni arhitektonski acceptance review** (Codex + Claude
zajedno, plan sekcija 20) prije nego što ima smisla krenuti na Prioritet C.

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

Izmjereno 2026-08-25 na `main`, post-merge gate nakon REF-06+REF-07
(merge `858b836`, `f541e0a`):

- `pytest tests/ -q` → **355 passed**, 11 warnings (deprecation
  warnings iz `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog
  koda), ~11-20s.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 48
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
DENT-022/DENT-023, `DENT-IMPROVE-007`/`009`, REF-00 do REF-07 su svi
zatvoreni (DONE). **Sljedeći na redu: REF-08 (Pi)** — zadnji task u
refaktor paketu (plan sekcija 15): theme/QSS izdvajanje, ukloniti
`desktop.fake_data` zavisnost iz produkcijskog View koda, provjeriti
PyInstaller build. Nakon toga: finalni arhitektonski acceptance review
(Codex + Claude, plan sekcija 20) prije nego što ima smisla krenuti na
Prioritet C (`DENT-IMPROVE-010`..`015`, Faza 1 priprema).

Podsjetnik: fizičan clean-machine test za `DENT-IMPROVE-009` (na drugoj
mašini) ostaje Radovanova provjera — implementacija/review su samo
simulirali to lokalno.
