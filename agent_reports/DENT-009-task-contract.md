---
task_id: DENT-009
risk: MEDIUM
implementer: codex
reviewer: claude
status: ASSIGNED
created_at: 2026-08-17
revised_at: 2026-08-18
---

# Task Contract — DENT-009 (REVIDIRAN — puni desktop dashboard)

**Ovo zamjenjuje prethodnu užu verziju ovog kontrakta.** Nijedan kod još
nije napisan za DENT-009 (provjereno — worktree ima samo ovaj fajl), pa
nema rada koji se gubi zamjenom. Radovan je dao novi, potpuniji mokap
("puni izgled desktop dashboarda") — obim je sada veći nego prvobitno:
ne samo sidebar + jedan panel, nego cio raspored ekran sa statusnim
ikonicama, blockout prikazom i tri desna panela.

Porijeklo mokapa: isti stil kao `docs/istrazivanje-dentalni-scheduler-gui.md`
(Open Dental/Curve/NexHealth patterns) — vidi tu sekciju 14 za koje
obrasce SU provjereni i preporučeni. Ne kopirati cio scope zrelih EHR
sistema — samo ono što je dole eksplicitno traženo.

## Cilj

Puni desktop "Raspored" ekran: sidebar (već planiran u prethodnoj
verziji) + gornja traka sa navigacijom/filterima + sedmični kalendar sa
statusnim ikonicama i blockout prikazom + tri desna panela (Novi
zahtjevi / Čekaju potvrdu / Otkazani danas) + "Sljedeći slobodan
termin" widget.

## Šta VEĆ POSTOJI i samo se poziva (ne piše iznova)

- `desktop/views/week_view.py` (DENT-003/006/010) — sedmični grid,
  boja-kodiranje po doktoru, multi-slot spajanje termina (`setSpan`),
  drag&drop. **Ne prepisivati logiku preklapanja/spajanja slotova** —
  samo dodati status ikonicu i blockout prikaz NA POSTOJEĆI mehanizam.
- `desktop/views/appointment_dialog.py` — dijalog za novi/izmijenjen
  termin, koristi se za "+ Novi termin" dugme.
- `src/dentaland/services/requests.py` — `list_pending()`,
  `confirm_request()`, `reject_request()` — VEĆ TESTIRANI (DENT-007),
  koriste se za "Novi zahtjevi" panel.
- `src/dentaland/services/booking.py` — `AppointmentService.all_combined()`,
  `doctors()` — postojeći upiti za termine/doktore.
- Doktor filter (Svi doktori/Ljubo/Zorka/Ana) — postoji kao tabovi
  (DENT-006), samo treba vizuelno preskinovati u segmentirano dugme sa
  slike ako lako ide, nije blokirajuće ako ostane kao tab red.

## Šta je NOVO u ovoj reviziji (ne postoji još)

### 1. Sidebar (kao i prije)

Raspored/Novi zahtjevi (sa brojem)/Pacijenti/Izvještaji/Postavke —
ostale stranice i dalje NAMJERNO placeholder ("Uskoro"), ne graditi
stvarne liste pacijenata/izvještaje/postavke.

**"Brzi pristup"** (novo na ovoj slici): Novi pacijent / Traži
pacijenta / Blokiraj vrijeme / Podsjetnici.
- "Novi pacijent" i "Traži pacijenta" zavise od Pacijenti funkcionalnosti
  koja NIJE u obimu — dugmad postoje vizuelno, klik otvara isti "Uskoro"
  placeholder kao i sama Pacijenti stranica. Ne graditi lažan CRUD.
- "Blokiraj vrijeme" MOŽE biti stvarno funkcionalno — `TimeOff` tabela
  već postoji u šemi (DENT-001). Ako vrijeme dozvoljava: mali dijalog
  (doktor, od/do datuma-vremena, razlog) koji upisuje `TimeOff` red.
  Ako ne stigneš, placeholder je prihvatljivo — javi kao
  `OUT_OF_SCOPE_FINDING` ako ostaje za kasnije.
- "Podsjetnici" — placeholder, van obima (Viber podsjetnici su Faza 2).

"Osoblje / Administrator" u dnu — i dalje SAMO statički tekst, bez
pravog login/RBAC (ponovljeno pravilo, nepromijenjeno).

### 2. Gornja traka

- "Raspored termina" / "Sedmični pregled zakazanih termina" — naslov,
  statičan tekst.
- "Danas" dugme + ‹ › strelice + prikaz opsega ("12 – 18. juni") —
  **ovo NE POSTOJI još.** `MainWindow` trenutno prima `week_start` samo
  jednom pri pokretanju (`desktop/views/main_window.py:26-38`), nema
  navigacije. Treba dodati: "Danas" resetuje na tekuću sedmicu, ‹ ›
  pomjeraju `week_start` za ±7 dana i pozivaju `week_view.refresh()`
  (ili rekreiraju week_view — po tvom nahođenju, šta je manje
  invazivno). Datumska ikonica sa "otvori kalendar" NIJE prioritet —
  može biti samo tekstualni prikaz opsega bez klika, javi kao manji
  `OUT_OF_SCOPE_FINDING` ako izostane.
- "+ Novi termin" — otvara postojeći `appointment_dialog.py`.
- "🖶 Štampa ▾" — **NIJE prioritet.** Placeholder dugme (može biti
  neaktivno/disabled sa tooltip-om "Uskoro") je prihvatljivo. Ne trošiti
  vrijeme na Qt print integraciju u ovom zadatku.

### 3. Doktor filter + "Prikaz" toggle

- Svi doktori/Ljubo/Zorka/Ana — postojeći filter, samo vizuelni stil.
- **"Prikaz: Po doktoru / Paralelno" — OTVORENO PITANJE, ne pogađaj.**
  Nejasno je tačno ponašanje (da li "Paralelno" znači posebna pod-kolona
  po doktoru unutar svakog dana, ili nešto drugo). Ovo je Radovanova
  odluka, ne tehnička pretpostavka. **Preporuka: implementiraj SAMO
  "Po doktoru" (postojeći kombinovani prikaz, već radi), stavi
  "Paralelno" dugme vizuelno ali neaktivno/disabled, i prijavi kao
  `OUT_OF_SCOPE_FINDING` sa pitanjem za Radovana.** Ne graditi nagađanu
  verziju "Paralelno" prikaza.
- Legenda boja doktora (• Dr Ljubo zeleno • Dr Zorka crveno • Dr Ana
  plavo) — boje već postoje (`_DOCTOR_PALETTE` u week_view.py), samo
  treba mali widget koji ih prikaže sa imenima pored filtera.

### 4. Statusne ikonice na terminima — TREBA NOVO POLJE U DTO

Legenda sa slike: ✓ Potvrđen / 🕐 Čeka potvrdu / 👤 Stigao / 💜 Završen /
✗ Otkazan-No-show.

**Šema za ovo već postoji** (DENT-012, upravo mergovano u ovaj trenutak
čeka review — provjeri da li je već u `main` prije nego počneš):
`Appointment.confirmed_at` i `Appointment.arrived_at`, oba nullable
timestamp, nezavisna od `status` enuma. Izvođenje ikonice iz podataka
(ovo je PRAVILO, ne pogađanje):

```text
status == CANCELLED ili NO_SHOW      → ✗ Otkazan/No-show
status == COMPLETED                   → 💜 Završen
status == SCHEDULED i arrived_at nije NULL   → 👤 Stigao
status == SCHEDULED i confirmed_at nije NULL (a arrived_at JESTE NULL) → ✓ Potvrđen
status == SCHEDULED i confirmed_at JESTE NULL → 🕐 Čeka potvrdu
```

Potreban rad (servisni sloj, `src/dentaland/services/booking.py`):
- Dodati `status`, `confirmed_at`, `arrived_at` polja na `AppointmentDTO`
  (trenutno ih DTO nema — namjerno izostavljena u DENT-012 dok nije
  postojao GUI koji ih koristi; sad postoji).
- Ažurirati `_to_dto()` da ih popunjava.
- Samo mapiranje "podaci → koja ikonica" (tabela iznad) može ići u
  `desktop/views/week_view.py` kao čisto prezentaciono pravilo (lookup
  tabela, ne poslovna logika) — to NIJE kršenje "logika ide u servisni
  sloj" pravila, isto kao što view već lokalno formatira
  `f"{appt.patient_name} — {appt.service}"`.

Potreban rad (popunjavanje polja — bez ovoga ikonice nikad neće
pokazati ništa osim "Čeka potvrdu"):
- `src/dentaland/services/requests.py::confirm_request()` — postaviti
  `confirmed_at = utcnow()` pri prelazu PENDING→SCHEDULED. Ovo je
  jednoredna izmjena u već testiranoj funkciji — dodaj/ažuriraj njen
  test da provjeri da se `confirmed_at` postavlja.
- Nova akcija "Označi stiglo" (mark arrived) — desni klik na termin u
  `week_view.py` ili dugme u `appointment_dialog.py`, poziva novu
  funkciju u `booking.py` (npr. `AppointmentService.mark_arrived(appt_id)`)
  koja postavlja `arrived_at = utcnow()`. Ovo JE nova servisna funkcija
  — napiši test za nju.
- Ručno kreirani termin direktno kroz `appointment_dialog.py` (ne kroz
  web zahtjev) — treba li automatski dobiti `confirmed_at` odmah pri
  kreiranju? **Facts vs Decisions**: tehnička činjenica je da trenutno
  ništa ne postavlja `confirmed_at` pri direktnom unosu; da li osoblje
  UVIJEK direktno potvrđuje termin koji sami unesu, ili treba da prođe
  kroz isti "čeka potvrdu" korak — to je Radovanova odluka, ne
  pretpostavljaj. Ako nije jasno, ostavi `confirmed_at = NULL` i
  konzervativno prijavi kao `OUT_OF_SCOPE_FINDING`/pitanje.

### 5. Blockout ("VAN ORDINACIJE") i pauza prikaz na kalendaru

- "VAN ORDINACIJE" siva kartica preko određenog vremenskog raspona —
  ovo je `TimeOff` red za tog doktora. Treba: upit koji vraća `TimeOff`
  zapise koji upadaju u prikazanu sedmicu (nova funkcija u `booking.py`,
  npr. `AppointmentService.time_off_for_week(week_start)`), i
  `week_view.py` renderuje te raspone kao neklikabilne sive ćelije
  (slično `setSpan` mehanizmu koji već postoji za termine — ponovna
  upotreba iste tehnike iz DENT-010, ne nova).
- "PAUZA" kartica (npr. 12:00-13:00) — ovo je razmak u `working_hours`
  za taj dan/doktora (split-shift, npr. jutro 08-12 pa popodne 13-20).
  `working_hours` šema to već podržava (više redova po danu). Prikazati
  razmak između dva `working_hours` reda istog dana kao "PAUZA" ćeliju.
  Ako doktor nema split-shift (samo jedan neprekinut raspon), nema
  PAUZA kartice tog dana — to je očekivano, ne bug.
- I blockout i pauza ćelije: NEKLIKABILNE (ne otvaraju dijalog za novi
  termin), ali NE MORAJU biti drag&drop mete — jednostavnije od termina.

### 6. Desni paneli — TRI RAZLIČITA IZVORA PODATAKA, NE MIJEŠATI

Ovo je najlakše pobrkati — svaki panel je DRUGAČIJI upit:

**"Novi zahtjevi (N)"** — `list_pending()` iz `requests.py`, VEĆ
POSTOJI i testiran (DENT-007). Ovo su PENDING zahtjevi sa javne forme —
NEMAJU dodijeljenu uslugu (`service_id` je NULL po dizajnu, vidi
`docs/dentaland-javna-forma-spec.md` — usluga se NE bira online).
**Mokap prikazuje "tip" (Pregled/Higijena/Estetika/Kanal) pored svakog
zahtjeva — ovo NIJE moguće sa stvarnim podacima i ne smije se
izmišljati.** Prikazati samo ime, traženi datum, i dugmad
Potvrdi/Odbij — bez tipa usluge. Ovo je ista razlika koju je DENT-009
prvobitni kontrakt već ispravno predviđao.

**"Čekaju potvrdu (N)"** — NOVO, NIJE isto što i "Novi zahtjevi".
Ovo su VEĆ ZAKAZANI termini (`status == SCHEDULED`, imaju pravo
`start_time`) čiji `confirmed_at` je i dalje NULL. Treba nova upit
funkcija u `booking.py` (npr. `AppointmentService.awaiting_confirmation()`).
Ovi IMAJU uslugu (dodijeljena pri zakazivanju), pa se tip stvarno može
prikazati.

**"Otkazani danas (N)"** — NOVO. Termini sa `status IN (CANCELLED,
NO_SHOW)` čiji je `start_time` DANAS. Nova upit funkcija (npr.
`AppointmentService.cancelled_today()`).

Sve tri liste: broj u zaglavlju = dužina liste, "Vidi sve" link može
biti neaktivan placeholder (nema pune "Termini" stranice još).

### 7. "Sljedeći slobodan termin"

Prikazuje doktora + datum/vrijeme prvog slobodnog slota. Ovo je
stvarni algoritam (traži prvi slot koji nije zauzet terminom ni
blokiran TimeOff-om, unutar working_hours) — **realno veći posao od
ostatka ovog zadatka.** Ako vrijeme ne dozvoljava punu implementaciju:
prihvatljivo je pojednostaviti na "prvi slobodan slot SLJEDEĆIH 7 DANA
za PRVOG doktora sa slobodnim terminom" (ne mora pretraživati sve
doktore optimalno), ili privremeno prikazati "Uskoro" ako je prekomplikovano
za ovaj krug — prijaviti kao `OUT_OF_SCOPE_FINDING` sa jasnim opisom šta
nedostaje, ne provoditi previše vremena ovdje na štetu ostatka zadatka.

## Dan-raspon kalendara — odluka 18.8.2026.

Radovan je na stvarnom prikazu dashboarda eksplicitno potvrdio da ordinacija
radi subotom i da interni sedmični raspored mora prikazivati šest kolona
Pon–Sub. `WeekView.DAY_NAMES` zato sadrži i `Sub`, `DAY_COUNT` je `6`, a
datumski raspon u zaglavlju završava subotom. Nedjelja se ne prikazuje.

## Footer na laptop ekranu — korekcija 18.8.2026.

Na stvarnom Windows prikazu pri sistemskom skaliranju donja statusna legenda i
sidebar blok „Osoblje / Administrator“ izlaze ispod vidljivog prostora. Sidebar
footer mora ostati izvan skrolabilnog navigacionog tijela, a `WeekView` mora
smjeti da se vertikalno sabije kako bi statusna legenda uvijek ostala vidljiva.
Naknadna provjera stvarno otvorenog prozora pokazala je da je statusna legenda
tehnički vidljiva, ali preniska i bez dovoljno vizuelnog odvajanja od kalendara.
Zato mora imati stabilnu visinu od najmanje 48 px, blago obojenu pozadinu i
čitljiviji tekst, bez izbacivanja bilo kog drugog sadržaja iz radne visine.
Svježi terminalski start je zatim otkrio stvarni uzrok odsijecanja: aplikacija
se otvara sa fiksnih 1536×1000 logičkih piksela, što pri Windows skaliranju
prelazi dostupnu radnu površinu i taskbar prekriva dno. Produkcijski entrypoint
zato mora otvoriti glavni prozor maksimizovan unutar Windows `availableGeometry`.

## Zaglavlje datuma — korekcija 18.8.2026.

Dvoredno zaglavlje dana i datuma ne smije odsijecati donji dio datuma pri
Windows skaliranju. Minimalna visina horizontalnog zaglavlja je 46 px.

## Poravnanje desnog panela — korekcija 18.8.2026.

Legenda doktora treba biti dio desne kolone i lijevom ivicom poravnata sa
naslovima kartica „Novi zahtjevi“, „Čekaju potvrdu“ i ostalim panelima, umjesto
da pluta desno u traci filtera. Naslovi `QGroupBox` kartica moraju biti blago
iznad gornjeg obruba, sa bijelom pozadinom iza teksta, tako da linija ne prolazi
kroz naslov.

## Terminologija statusa — korekcija 18.8.2026.

Korisnički vidljiva oznaka `No-show` u statusnoj legendi prevodi se na srpski
kao „Nije došao“. Interni enum `NO_SHOW` ostaje nepromijenjen.

## Satne ćelije rasporeda — korekcija 18.8.2026.

Svaki red mreže predstavlja jedan puni sat: 08:00, 09:00, 10:00 itd. Ne postoje
dvije odvojene polusatne ćelije unutar istog sata. Satni red je samo vizuelni
orijentir rasporeda i ne propisuje medicinsko trajanje pregleda. Stvarno
trajanje određuje doktor; kartica prikazuje sačuvano početno i završno vrijeme.
Postojeći kraći termini ostaju vidljivi u satnoj ćeliji u kojoj počinju, a
termini koji prelaze granicu sata obuhvataju sve pogođene satne redove.

## allowed_paths (PROŠIRENO u odnosu na prvobitnu verziju)

```yaml
allowed_paths:
  - desktop/views/main_window.py
  - desktop/app.py
  - desktop/views/sidebar.py
  - desktop/views/requests_panel.py
  - desktop/views/stub_page.py
  - desktop/views/week_view.py          # NOVO — status ikonice + blockout
  - desktop/views/appointment_dialog.py  # NOVO — "označi stiglo" akcija
  - src/dentaland/services/booking.py    # NOVO — DTO polja + nove upit funkcije
  - src/dentaland/services/requests.py   # NOVO — confirm_request postavlja confirmed_at
  - tests/test_gui/test_main_window.py
  - tests/test_gui/test_app.py
  - tests/test_gui/test_requests_panel.py
  - tests/test_gui/test_week_view.py
  - tests/test_services.py
  - tests/test_requests.py
  - agent_reports/**
forbidden_paths:
  - src/dentaland/models.py    # šema se NE mijenja ovim zadatkom
  - migrations/**
  - backend/**
  - web/**
  - CLAUDE.md
  - AGENTS.md
```

**Prije početka: pozvati `coordination.py claim` za sve gornje putanje**
— `week_view.py`/`booking.py`/`requests.py` nisu bile u prvobitnom
DENT-009 obimu, provjeri da nema aktivnog claim-a od drugog zadatka
(u trenutku pisanja ovog kontrakta nema kolizije, ali provjeri ponovo
jer se stanje mijenja).

## acceptance (dopunjeno)

- Sve iz prvobitnog kontrakta (sidebar, Novi zahtjevi tok, placeholder
  stranice, nula SQLAlchemy importa u `desktop/views/`) i dalje važi.
- Status ikonica na svakom terminu odgovara tabeli iz sekcije 4,
  testirano nad seed-ovanim podacima sa svih 5 kombinacija stanja.
- `confirm_request()` postavlja `confirmed_at`; postoji test za to.
- Nova `mark_arrived()` funkcija testirana (uspjeh + slučaj nepostojećeg
  ID-a).
- Blockout/pauza ćelije se prikazuju iz stvarnih `TimeOff`/`working_hours`
  podataka, ne hardkodovano; neklikabilne su.
- "Novi zahtjevi" panel NE prikazuje izmišljen tip usluge.
- Sedmični raspored i datumski raspon prikazuju Pon–Sub; nedjelja nije kolona.
- Statusna legenda i sidebar staff footer vidljivi su i na visini prozora 760 px;
  statusna legenda je visoka najmanje 48 px i jasno odvojena od kalendara.
- `desktop.app.main()` otvara prozor maksimizovan tako da taskbar ne prekriva
  donji dio aplikacije; ponašanje je pokriveno testom entrypointa.
- Naziv dana i puni datum vidljivi su u dvorednom zaglavlju bez odsijecanja.
- Legenda doktora počinje na lijevoj ivici desne kolone, a naslov svake desne
  kartice je čitljiv iznad obruba bez linije kroz tekst.
- Statusna legenda prikazuje „Otkazan / Nije došao“ i ne sadrži engleski izraz
  `No-show`.
- Raspored od 08:00 do 20:00 ima 12 satnih redova, bez odvojene polusatne
  ćelije za unos.
- Lijeva vremenska skala prikazuje neodsječene pune sate u zaglavlju širine
  najmanje 60 px.
- Nijedan tekst ni poslovno pravilo ne tvrdi da prvi pregled traje 30, 60 ili
  drugi fiksni broj minuta; satni red je samo vizuelni orijentir.
- "Čekaju potvrdu" i "Otkazani danas" koriste ispravan, različit upit
  (ne isti kao "Novi zahtjevi").
- Sve preostale `OUT_OF_SCOPE_FINDING` stavke iz ovog kontrakta (Paralelno
  prikaz, Štampa, kalendar-ikonica za datum i "Sljedeći slobodan termin"
  pojednostavljenje) eksplicitno prijavljene u evidence
  fajlu, ne prećutno izostavljene.

## verification

```yaml
verification:
  - pytest tests/ -q
  - ruff check src/dentaland desktop tests
  - "grep -ri sqlalchemy desktop/views/*.py  # očekivano prazno"
  - mypy src/dentaland desktop  # baseline provjera, 8 postojećih grešaka, nula novih
review:
  reviewers: 1
  required: [architecture, scope]
```
