---
task_id: DENT-009
risk: MEDIUM
implementer: codex
reviewers: [claude]
verdict: PENDING_REVIEW
commits: []
created_at: 2026-08-17
---

# DENT-009 — puni desktop dashboard

## Task Contract

Izvor: `agent_reports/DENT-009-task-contract.md` (revidirana puna verzija).

## Šta je urađeno

- Glavni raspored dobio je sidebar, brzi pristup, gornju sedmičnu navigaciju,
  doktor filter, neaktivni `Paralelno` prikaz, dugme za novi termin, legendu i
  tri odvojena desna panela.
- `Novi zahtjevi`, `Čekaju potvrdu` i `Otkazani danas` koriste tri različita
  servisna upita. Javni zahtjev ne prikazuje izmišljenu uslugu.
- Potvrda javnog zahtjeva postavlja `confirmed_at`; dodana je servisna akcija
  `mark_arrived()` i kontekstna akcija `Označi stiglo` na terminu.
- `AppointmentDTO` prenosi status, `confirmed_at` i `arrived_at`; kalendar
  prikazuje ugovorene ikonice za svih pet stanja.
- `TimeOff` i split-shift razmaci iz `working_hours` prikazuju se kao spojeni,
  sivi i neklikabilni rasponi.
- Ostale sidebar stranice su namjerni `Uskoro` placeholderi.
- GUI eksplicitno postavlja svijetlu Qt paletu i svijetle stilove za prozor,
  sidebar, kalendar, panele, kontrole i scroll površine, pa više ne nasljeđuje
  tamnu Windows temu suprotno mokapu.
- Naknadni, detaljniji mokap od 17.8.2026. primijenjen je kao nova vizuelna
  referenca: sidebar je proširen i presložen, kalendar prikazuje 08:00–20:00,
  uvedeni su Dan/Sedmica segment, doktor legenda
  uz filtere, statusna legenda ispod grida i kartica sljedećeg slobodnog termina.
- Završno poređenje sa stvarnim screenshotom i mokapom zamijenilo je emoji/glyph
  navigaciju skalabilnim SVG linijskim ikonama, dodalo puni Dentaland wordmark,
  aktivno teal stanje navigacije i crveni broj novih zahtjeva.
- Zamjenski nacrtani zub u brand bloku zamijenjen je stvarnim Dentaland logom iz
  `web/assets/logo.png`; horizontalni wordmark je zadržan radi čitljivosti.
- Termini i blockout rasponi sada su zaobljene, uvučene kartice sa nježnom bojom
  doktora, vremenom i statusom; mreža rasteže 24 slota na raspoloživu visinu i
  više ne prikazuje unutrašnji vertikalni scrollbar.
- Desni paneli su vizuelno zbijeni prema mokapu; uklonjen je izmišljeni tekst
  „Dr Ana“ iz privremenog widgeta sljedećeg slobodnog termina.
- Odlukom od 18.8.2026. sedmični raspored prikazuje šest kolona Pon–Sub, a
  raspon datuma u zaglavlju završava subotom; nedjelja se ne prikazuje.
- Footer korekcija od 18.8.2026. odvaja „Osoblje / Administrator“ od
  skrolabilnog navigacionog tijela i dopušta kalendaru vertikalno sabijanje,
  tako da sidebar footer i statusna legenda ostaju vidljivi na laptop ekranu.
- Dvoredno zaglavlje kalendara povećano je sa 38 na 46 px kako Windows
  skaliranje više ne bi odsijecalo donji dio datuma.

## Verifikacija

- `pytest -q` — PASS: **102 passed**, 11 dependency/deprecation upozorenja.
- `ruff check src/dentaland desktop tests` — PASS.
- `mypy src/dentaland desktop` — **7 postojećih grešaka** u tri ranija GUI
  modula (ugovor je očekivao baseline 8); nema novih grešaka u novim DENT-009
  modulima, dakle baseline je smanjen za jednu.
- pretraga `sqlalchemy` u `desktop/views` — prazno, PASS.
- `git diff --check` — PASS (samo Git LF→CRLF upozorenja na Windowsu).
- regresija svijetle teme: `24 passed` u ciljanim GUI testovima; Ruff PASS.
- nakon detaljnog usklađivanja: puni suite **103 passed**, Ruff PASS, mypy ostaje
  na istih 7 ranijih GUI nalaza bez novih DENT-009 nalaza.
- završna vizuelna iteracija: puni suite **103 passed**, `ruff check src/dentaland
  desktop tests` PASS i `git diff --check` PASS (samo LF→CRLF upozorenja).
- offscreen render 1536×1000 napravljen radi provjere proporcija; stvarni tekst
  u tom renderu nije korišten kao dokaz tipografije jer sandbox nema pristup
  sistemskom Windows fontu, dok se font provjerava pri normalnom pokretanju.
- Pon–Sub follow-up: ciljani GUI testovi **30 passed**, puni suite **105 passed**,
  Ruff PASS i `git diff --check` PASS.
- Footer follow-up: ciljani GUI testovi **26 passed**, uključujući prozor visine
  760 px; puni suite **106 passed**, Ruff PASS i `git diff --check` PASS.
- Header follow-up: ciljani GUI testovi **26 passed**, puni suite **106 passed**,
  Ruff PASS i `git diff --check` PASS; test potvrđuje visinu zaglavlja 46 px.

## Review

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisno provjereno (ne samo pročitano):

- `pytest tests/ -q` → **104 passed** (worktree, malo se razlikuje od
  prijavljenih 103 — beznačajno, i dalje sve prolazi).
- `ruff check src/dentaland desktop tests` → PASS.
- `mypy src/dentaland desktop` → **7 grešaka** (baseline je bio 8, sada
  potvrđeno smanjen za jedan — nula novih iz DENT-009 koda).
- `grep -ri sqlalchemy desktop/views/*.py` → prazno, PASS.
- Pokrenuta stvarna GUI aplikacija (offscreen render, `QT_QPA_PLATFORM=offscreen`)
  sa seed-ovanim podacima (3 termina različitih doktora/statusa + jedan
  `TimeOff`): 60-minutni termin ispravno vizuelno spojen preko 2 ćelije,
  `TimeOff` blok ispravno spojen preko 4 ćelije (14–16h) i sivo obojen,
  boja-kodiranje po doktoru prisutno. Napomena: sandbox offscreen render
  nema pristup sistemskim fontovima (isti nalaz koji je implementer već
  prijavio), pa fina tipografska/vizuelna provjera nije potpuno pouzdana
  ovim putem — konačna vizuelna potvrda treba doći sa Radovanovog
  stvarnog pokretanja.
- Pregledan kod (ne samo verifikacija): `confirm_request()` ispravno
  postavlja `confirmed_at = utcnow()`; `mark_arrived()` ispravno odbija
  ne-SCHEDULED termine (`ValueError`); `awaiting_confirmation()` i
  `cancelled_today()` tačno prate specifikaciju iz Task Contracta
  (različiti upiti, timezone-aware); `time_off_for_week()` i
  `breaks_for_week()` ispravno klipuju raspone na vidljivu sedmicu i
  detektuju split-shift razmake; `status_icon()` u `week_view.py` je
  čista prezentaciona lookup funkcija (ne poslovna logika) koja tačno
  prati tabelu iz kontrakta.

Svih šest `OUT_OF_SCOPE_FINDING` zapisa su razumni i ispravno prijavljeni
umjesto nagađani (Paralelno prikaz, Štampa/date-picker, sljedeći
slobodan termin algoritam, Pon–Pet vs Pon–Sub raspored — ovo zadnje
vrijedi napomenuti Radovanu jer se javna forma odlučila za Pon–Sub, a
interni raspored sada prati noviji mokap sa Pon–Pet, nedosljednost
između dvije površine, poslovna odluka nije tehnička), manuelni unos i
`confirmed_at`. Nijedan nije tiho pretpostavljen.

`PASS_WITH_NOTES` umjesto čistog `PASS` samo zbog sandbox vizuelne
neizvjesnosti gore — kod, testovi i arhitektura su bez primjedbi.

**Follow-up 18.8.2026:** nakon ovog reviewa Radovan je donio poslovnu odluku da
desktop raspored mora prikazivati subotu. Izmjena Pon–Pet → Pon–Sub je automatski
verifikovana, ali zahtijeva kratki nezavisni follow-up review prije merge-a;
gornji verdict ostaje istorijski zapis pregleda prethodne verzije.

Istog dana je nakon stvarnog screenshot pregleda dodana i responzivna footer
korekcija; ona je pokrivena determinističkim geometrijskim GUI testom i ulazi u
isti follow-up review.

**Follow-up review (Claude, 18.8.2026) — PASS.** Nezavisno provjereno:
`WeekView.DAY_COUNT = 6`, `DAY_NAMES = ["Pon","Uto","Sri","Čet","Pet","Sub"]`
(`desktop/views/week_view.py:71-72`) — javna forma i interni raspored su sada
usklađeni (oboje Pon–Sub). `pytest tests/ -q` → **106 passed** (nula pada),
`ruff check src/dentaland desktop tests` → PASS, `mypy src/dentaland desktop`
→ **7 grešaka**, isti baseline kao prethodni review, nula novih. Nema
regresije od prvobitnog PASS_WITH_NOTES pregleda.

**Follow-up implementacija (Codex, 18.8.2026) — Windows footer.** Svježi
terminalski start na Radovanovom ekranu pokazao je da prethodni geometrijski
test nije obuhvatio Windows DPI + taskbar kombinaciju: početni
`resize(1536, 1000)` davao je prozor viši od dostupne radne površine pa je
taskbar prekrivao footer. `desktop.app.main()` sada koristi
`showMaximized()`, restore veličina je smanjena na 1280×720, a statusna legenda
ima stabilnih 48 px i jasnije vizuelno odvajanje. Dodan je entrypoint test koji
provjerava maksimizovano otvaranje. Verifikacija poslije izmjene:
`pytest tests -q` → **107 passed**, `ruff check src/dentaland desktop tests` →
PASS. Ova naknadna izmjena zahtijeva kratki follow-up review prije merge-a.

**Follow-up review (Claude, 18.8.2026) — PASS.** Footer/DPI fix
nezavisno provjeren: `desktop/app.py` sada zove `window.showMaximized()`
umjesto fiksnog `resize()` — koristi punu radnu površinu iznad Windows
taskbara, ispravno rješava nalaz sa Radovanovog ekrana. Novi test
`test_main_otvara_prozor_maksimizovan` ispravno provjerava REDOSLIJED
poziva (mock `QApplication`/`AppointmentService`/`MainWindow`, provjera
da je `showMaximized()` pozvan prije `exec()`) — pravi test ponašanja,
ne samo da metoda postoji. `pytest tests/ -q` → **107 passed**, `ruff
check src/dentaland desktop tests` → PASS, `mypy src/dentaland desktop`
→ **7 grešaka**, isti baseline, nula novih. Nema regresije.

Svih šest `OUT_OF_SCOPE_FINDING` zapisa (Paralelno prikaz, Štampa/
date-picker, sljedeći slobodan termin, Blokiraj vrijeme/ostali sidebar
placeholderi, manuelni unos i `confirmed_at`) su i dalje razumno
prijavljeni i dogovoreni sa Radovanom kao sljedeći koraci (vidi
`CLAUDE.md`) — nijedan nije tiho riješen niti zaboravljen.

**Follow-up implementacija (Codex, 18.8.2026) — poravnanje desne kolone.**
Legenda doktora je izmještena iz globalne filter trake u vrh desne kolone i
poravnata sa lijevom ivicom naslova dashboard kartica. Naslovi `QGroupBox`
kartica podignuti su 3 px, uz povećan gornji margin i bijelu podlogu iza teksta,
pa obrub više ne prolazi kroz naslov. Dodat je GUI geometrijski test poravnanja.
Verifikacija: `pytest tests -q` → **108 passed**; `ruff check src/dentaland
desktop tests` → PASS. Ova vizuelna korekcija čeka kratki follow-up review.

**Follow-up implementacija (Codex, 18.8.2026) — srpska oznaka statusa.**
Korisnički tekst „Otkazan / No-show“ zamijenjen je sa „Otkazan / Nije došao“;
interni `NO_SHOW` enum nije mijenjan. GUI test eksplicitno provjerava prevedeni
tekst i odsustvo engleske oznake.

**Follow-up implementacija (Codex, 18.8.2026) — čitljivost kartice termina.**
Uzrok nečitkog prikaza nakon zakazivanja bio je sadržaj sa prevelikim marginama
i unutrašnjim razmakom u niskoj kartici. Kraći termin sada koristi kompaktan
dvoredni prikaz: ime pacijenta u prvom redu, a puni vremenski raspon, status i
doktor u drugom; duži termini zadržavaju detaljni prikaz. Vremenska skala ima
12 satnih redova, uz zaglavlje širine 64 px i desno poravnanje, pa oznake više
nisu zbijene niti odsječene. Testovi provjeravaju sadržaj i geometriju oba
režima te oznake vremenske skale.
`pytest tests -q` → **108 passed**; `ruff check src/dentaland desktop tests` →
PASS. GitNexus je
centralni `WeekView.refresh()` označio kao CRITICAL blast-radius (13 direktnih
pozivalaca), zbog čega je izvršen puni test paket. Korekcija čeka kratki
follow-up review.

**Follow-up review (Claude, 18.8.2026) — PASS.** Oba naknadna commit-a
nezavisno provjerena:

- Poravnanje desne kolone: legenda doktora premještena iz reda filtera
  u zaseban red iznad `dashboard_panels`, poravnata sa lijevom ivicom
  panela; `QGroupBox::title` dobija bijelu pozadinu i pomjerenu poziciju
  da obrub ne siječe naslov. Vizuelno razumno, potvrđeno geometrijskim
  testom (ne samo tvrdnja da izgleda dobro).
- Prevod statusa: `NO_SHOW` enum ostaje netaknut (provjereno —
  `grep NO_SHOW src/dentaland/models.py` nepromijenjen), samo
  korisnički prikazan tekst je lokalizovan. Ispravna razdvojenost
  internog identifikatora od prikaza. Test provjerava i prisustvo
  novog teksta i odsustvo engleskog izraza — nije moglo tiho da se
  provuče djelimično urađeno.

Nezavisno pokrenuto: `pytest tests/ -q` → **108 passed**, `ruff check
src/dentaland desktop tests` → PASS, `mypy src/dentaland desktop` →
**7 grešaka** (isti baseline, nula novih), `grep -ri sqlalchemy
desktop/views/*.py` → prazno. Nema regresije.

## Integration status

**Follow-up implementacija (Codex, 18.8.2026) — satne ćelije.** Prva
interpretacija screenshota bila je pogrešna: mreža je ostala podijeljena na
dvije polusatne ćelije. Ispravka sada postavlja satne vizuelne redove, pa
raspored od 08:00 do 20:00 ima 12 redova. Satni red nije tvrdnja o trajanju
pregleda: kartica prikazuje stvarni sačuvani vremenski raspon, a trajanje
određuje doktor. Ne postoji pravilo „prvi pregled traje 30 minuta“.

**Follow-up review (Claude, 18.8.2026) — PASS.** Nezavisno provjereno:
`SLOT_MINUTES` (stvarna granularnost grida) je NEPROMIJENJEN — samo je
prikaz vremenske oznake u zaglavlju smanjen na svaki drugi red (puni
sat, `i % 2 == 0`) uz širi (64px), desno poravnat stubac oznaka, i
kartica termina sad ima dva vizuelna režima: kompaktan dvoredni prikaz
za termine ≤ `SLOT_MINUTES`, detaljan troredni za duže. Ovo je čisto
prezentaciona izmjena, ne dira logiku trajanja/preklapanja termina —
potvrđeno čitanjem diffa (nema izmjene u `_check_overlap`/`_to_dto`/
`SLOT_MINUTES` definiciji). Ispravka teksta u evidence/kontrakt fajlu
(uklonjena netačna tvrdnja o "60 minuta podrazumijevano") je ispravna
samoispravka — takvo pravilo nikad nije odlučeno, dobro da nije ostalo
upisano kao činjenica.

`pytest tests/ -q` → **108 passed**, `ruff check src/dentaland desktop
tests` → PASS, `mypy src/dentaland desktop` → **7 grešaka** (isti
baseline, nula novih), `grep -ri sqlalchemy desktop/views/*.py` →
prazno. Nema regresije.

MERGED → INTEGRATION_VERIFIED → DONE. Prvobitna implementacija
mergovana (107 passed); follow-up "poravnanje desne kolone + srpski
prevod statusa" mergovan naknadno (108 passed); follow-up "čitljivost
kartica + satni red kalendara" mergovan naknadno. Post-merge
integration gate poslije zadnjeg follow-up merge-a: 108 passed, ruff
čist, mypy baseline nepromijenjen (7/7), nula SQLAlchemy importa u
desktop/views/.

## Odbačene opcije

- Nije napravljen novi kalendarski grid: proširen je postojeći `WeekView` i
  njegova `setSpan` logika.
- Nije izmišljena usluga za javni zahtjev jer taj podatak ne postoji prije
  potvrde u ordinaciji.
- Nije implementirano nagađano ponašanje `Paralelno` prikaza.

## OUT_OF_SCOPE_FINDING

```yaml
finding: OUT_OF_SCOPE_FINDING
description: Nije definisano da li Paralelno znači pod-kolone po doktoru ili drugi prikaz; dugme je vidljivo i neaktivno.
location: desktop/views/main_window.py
risk: MEDIUM
proposed_task: Poslovno definisati Paralelno prikaz pa otvoriti poseban GUI zadatak.
```

```yaml
finding: OUT_OF_SCOPE_FINDING
description: Štampa i klikabilni birač datuma ostaju placeholderi.
location: desktop/views/main_window.py
risk: LOW
proposed_task: Implementirati Qt print i date-picker u zasebnom zadatku.
```

```yaml
finding: OUT_OF_SCOPE_FINDING
description: Sljedeći slobodan termin nije implementiran jer zahtijeva zaseban algoritam nad working_hours, TimeOff i zauzećima.
location: src/dentaland/services/booking.py
risk: MEDIUM
proposed_task: Dodati servisni slot-search i njegov dashboard widget.
```

### Razriješen nalaz — subota

Poslovna odluka je donesena 18.8.2026: ordinacija radi subotom i desktop
raspored prikazuje Pon–Sub. Prethodni `OUT_OF_SCOPE_FINDING` je zatvoren kroz
`WeekView.DAY_COUNT = 6`, zaglavlje `Sub` i test datuma završetka sedmice.

```yaml
finding: OUT_OF_SCOPE_FINDING
description: Blokiraj vrijeme i sidebar Pacijenti/Izvještaji/Postavke/Podsjetnici su namjerni placeholderi.
location: desktop/views/sidebar.py
risk: LOW
proposed_task: Implementirati svaku funkcionalnost kroz zaseban Task Contract.
```

```yaml
finding: OUT_OF_SCOPE_FINDING
description: Ručno kreirani termini ostaju bez confirmed_at i zato čekaju potvrdu; poslovna odluka o automatskoj potvrdi nije donesena.
location: src/dentaland/services/booking.py
risk: MEDIUM
proposed_task: Radovan/Ljubo da potvrde pravilo pa ga pokriti servisnim testom.
```
