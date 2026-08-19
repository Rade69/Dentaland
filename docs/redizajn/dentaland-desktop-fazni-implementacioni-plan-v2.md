# Dentaland Desktop — fazni implementacioni plan UX/UI redizajna schedulera

**Verzija:** 2.0 — revidirano nakon Claude review-a  
**Datum:** 19.08.2026.  
**Osnova:** prethodni implementacioni plan + pregled stvarnog `main` koda + Claude review  
**Princip:** ovo više NIJE jedan veliki Task Contract. Implementacija je podijeljena u 6 nezavisnih faza sa zasebnim scope-om, testovima, evidence paketom i review tačkama.

---

# 0. Zaključane odluke prije implementacije

Ove odluke imaju prednost nad starim mockupima i starom verzijom plana.

## 0.1 Status u `Detalji termina`

NE koristiti dropdown sa svim statusima.

Razlog:
- `confirmed_at` i `arrived_at` nisu isti tip stanja kao `COMPLETED`, `NO_SHOW`, `CANCELLED`;
- dropdown bi sugerisao proizvoljne povratne tranzicije;
- završeni, no-show i otkazani termini su read-only u normalnom toku.

Koristiti:

```text
Trenutni status
[ status badge ]

Dostupne akcije prema trenutnom stanju
```

Za aktivan `SCHEDULED` mogu se ponuditi samo relevantne akcije:

```text
Potvrdi termin
Pacijent je stigao
Označi kao završen
Označi kao "nije došao"
Otkaži termin
```

Ne prikazivati akciju koja je već izvršena.

`COMPLETED`, `NO_SHOW`, `CANCELLED` su terminalna/read-only stanja u ovom tasku.

---

## 0.2 Vrijeme u `Obradi zahtjev`

Mockup sa dugmadima:

```text
09:00  09:30  10:00 ...
```

NIJE obavezujući.

Dok aplikacija nema stvarni availability-slot generator, koristiti stilizovani:

```text
QTimeEdit
```

ili postojeću odgovarajuću kontrolu.

Ne hardkodovati slotove koji izgledaju kao provjerena dostupnost.

Slot-picker je buduća nadogradnja kada postoji pravi availability servis.

---

## 0.3 Donji statusni summary OSTAVLJAMO

Prethodni plan je tražio uklanjanje statusne trake. Ta odluka je povučena.

Traka je u međuvremenu pretvorena u živi brojač i ostaje.

Primjer:

```text
✓ Potvrđen (2) | ◷ Čeka potvrdu (0) | ● Stigao (1) | ...
```

Pravila:

- informativni summary;
- nije filter;
- ne smije vizuelno izgledati kao clickable control;
- mora se osvježavati nakon statusnih promjena;
- eventualni pravi status filter je zaseban budući task.

---

## 0.4 Hard delete je zaseban HIGH-risk task

`Izbriši termin` nije dio običnog MEDIUM GUI refactora.

Hard delete je:
- nepovratan;
- uklanja pacijentski zapis termina;
- zahtijeva zaseban Task Contract;
- zahtijeva pojačan review;
- zahtijeva eksplicitni human approval prije merge-a.

Ostatak redizajna ne smije zavisiti od toga da hard delete bude implementiran odmah.

UI može dobiti `Izbriši termin` tek u Fazi F.

---

## 0.5 `_check_overlap(..., exclude_id=...)` već postoji

Ne širiti helper bez potrebe.

Trenutni kod već podržava:

```python
exclude_id: int | None = None
```

i `move()` ga koristi.

Za `update()` koristiti postojeće:

```python
_check_overlap(..., exclude_id=appt_id)
```

Obavezno testirati da termin pri editovanju ne kolidira sam sa sobom.

---

# 1. Globalni UX cilj

Ne praviti novi dashboard od nule.

Zadržati:
- sidebar;
- centralni scheduler;
- doctor filter;
- `Dan / Sedmica`;
- `Novi termin`;
- `Štampa`;
- desni operativni panel;
- postojeći Dentaland teal/white/navy stil;
- pastelne boje doktora;
- postojeći statusni summary.

Glavni mentalni model:

```text
Prazan slot + lijevi klik
    -> Novi termin

Postojeći termin + lijevi klik
    -> Detalji termina

Postojeći termin + desni klik
    -> Brze akcije

Drag & drop
    -> Direktno pomjeranje
```

---

# 2. Pravila rada agenata

Svaka faza je zaseban Task Contract.

Prije svake faze:

1. pročitati `AGENTS.md`;
2. pročitati `CLAUDE.md`;
3. provjeriti trenutno stanje brancha;
4. provjeriti da prethodna faza jeste merge-ovana;
5. pokrenuti relevantne postojeće testove;
6. claimovati samo fajlove potrebne toj fazi.

Ne započinjati narednu fazu ako prethodna nije prošla review.

Svaka faza mora završiti sa:
- testovima;
- ruff provjerom relevantnog scope-a;
- task-specific evidence fajlom;
- listom izmijenjenih fajlova;
- poznatim ograničenjima.

---

# FAZA A — Service capabilities za edit i statuse

**Risk:** MEDIUM  
**Zavisnosti:** nema  
**Cilj:** napraviti backend/service osnovu koju će GUI kasnije koristiti.  
**Ne uključuje:** hard delete.

## A.1 Dozvoljene putanje

```text
src/dentaland/services/booking.py
src/dentaland/services/__init__.py
tests/test_services.py
agent_reports/**
```

Ne dirati:
```text
desktop/**
src/dentaland/models.py
migrations/**
```

## A.2 Implementirati `update(...)`

Mora omogućiti:
- promjenu pacijenta;
- telefona;
- emaila;
- doktora;
- usluge;
- napomene;
- start/end vremena.

Overlap:
- provjera za NOVOG doktora;
- koristiti postojeći `_check_overlap`;
- obavezno `exclude_id=appt_id`;
- jedna transakcija;
- vratiti `AppointmentDTO`.

Ne dodavati novi overlap framework.

## A.3 Implementirati statuse

Dodati eksplicitne service metode:

```python
mark_completed(appt_id)
mark_no_show(appt_id)
```

Postojeće zadržati:

```python
mark_confirmed
mark_arrived
cancel
```

Ne praviti generički:

```python
set_status(anything)
```

Terminalna stanja u ovom tasku:

```text
COMPLETED
NO_SHOW
CANCELLED
```

Ne implementirati restore/reopen.

## A.4 Service options sa trajanjem

GUI mora moći dobiti:
- service id;
- naziv;
- `trajanje_min`;
- po mogućnosti buffer ako već postoji i relevantan je.

Preporuka:

```python
ServiceOptionDTO
```

ili ekvivalentan stabilan read model.

Ne hardkodovati sva trajanja na 60 minuta.

## A.5 Testovi

Obavezno:
- update mijenja podatke;
- update mijenja doktora;
- update mijenja vrijeme;
- update odbija pravi overlap;
- update NE vidi sam sebe kao overlap;
- completed radi;
- no-show radi;
- terminalna/nevažeća tranzicija daje jasan error;
- service option vraća duration.

## A.6 Definition of Done

- [ ] GUI nije diran;
- [ ] nema migracije;
- [ ] `update` radi sa `exclude_id`;
- [ ] status metode postoje;
- [ ] service duration je dostupan;
- [ ] svi relevantni service testovi prolaze.

**STOP / REVIEW A**

---

# FAZA B — Vizuelni sistem modala + Unified Novi/Uredi termin

**Risk:** MEDIUM  
**Zavisnost:** Faza A  
**Cilj:** ukloniti generički create workflow i napraviti jedan kvalitetan editor.

## B.1 Dozvoljene putanje

```text
desktop/views/appointment_dialog.py
desktop/views/main_window.py
desktop/views/dialogs/**
tests/test_gui/test_appointment_dialog.py
tests/test_gui/test_main_window.py
agent_reports/**
```

Service sloj se ne mijenja osim ako review Faze A zahtijeva minimalnu korekciju.

## B.2 `BaseDialog`

Napraviti reusable vizuelnu osnovu za glavne modalne tokove.

Stil:
- white background;
- dark navy text;
- postojeći Dentaland teal;
- 10–12 px radius;
- blag border/shadow;
- custom header;
- custom footer;
- bez generičkog `QDialogButtonBox` izgleda;
- SVG ikone gdje postoje.

Bez emoji ikona.

## B.3 `AppointmentEditorDialog`

Jedan dialog za:

```text
Novi termin
Uredi termin
```

Polja:

```text
Pacijent *
Telefon
Email
Doktor *
Datum *
Vrijeme *
Trajanje *
Usluga *
Napomena
```

Create mode:
- prazan slot prefilluje datum/vrijeme;
- aktivni doctor filter preselectuje doktora;
- `Svi doktori` -> doktor se bira u ISTOM modalu;
- nema `QInputDialog("Koji doktor?")`.

Edit mode:
- postojeći DTO prefilluje polja;
- save koristi `update(...)`.

## B.4 Trajanje

Kada korisnik izabere uslugu:
- predložiti `trajanje_min` iz service optiona;
- trajanje ostaje vidljivo;
- ne koristiti univerzalnih 60 min kao jedinu logiku.

## B.5 Inline greške

Overlap/validation se prikazuju u modalu.

Primjer:

```text
Termin se preklapa sa postojećim terminom Dr Ljube.
Izaberite drugo vrijeme ili doktora.
```

Modal ostaje otvoren.

Status bar ne koristiti kao glavni error feedback za ovaj tok.

## B.6 MainWindow cleanup

Ukloniti:
```python
QInputDialog
_doctor_for_new_appointment()
```

MainWindow ostaje orkestrator, ne mjesto gdje se gradi cijeli dialog.

## B.7 Testovi

- create mode;
- edit mode;
- doctor preselection;
- service duration default;
- required validation;
- overlap ne zatvara dialog;
- save create;
- save edit;
- nema više doctor QInputDialog toka.

## B.8 Definition of Done

- [ ] jedan unified editor;
- [ ] create i edit rade;
- [ ] doktor je unutar modala;
- [ ] duration dolazi iz usluge;
- [ ] generički OK/Cancel izgled uklonjen;
- [ ] postojeći scheduler nije funkcionalno regresiran.

**STOP / REVIEW B**

---

# FAZA C — Detalji termina + klik + context menu + pomjeranje/otkazivanje

**Risk:** MEDIUM  
**Zavisnosti:** A + B  
**Cilj:** napraviti jasan operativni model rada sa postojećim terminom.  
**Hard delete NIJE dio ove faze.**

## C.1 Putanje

```text
desktop/views/week_view.py
desktop/views/main_window.py
desktop/views/dialogs/appointment_details.py
desktop/views/dialogs/move_appointment.py
desktop/views/dialogs/cancel_appointment.py
tests/test_gui/test_week_view.py
tests/test_gui/test_main_window.py
tests/test_gui/test_appointment_details_dialog.py
tests/test_gui/test_destructive_dialogs.py
agent_reports/**
```

## C.2 Lijevi klik

Dodati:

```python
appointment_clicked = Signal(int)
```

Ponašanje:
- prazan slot -> postojeći create flow;
- appointment -> `Detalji termina`.

`WeekView` ne otvara dialog sam.

## C.3 `Detalji termina`

Prikazati:
- ime;
- telefon;
- email;
- datum;
- vrijeme;
- trajanje;
- doktor;
- usluga;
- napomena;
- trenutno stanje.

### VAŽNO — status NIJE dropdown

Prikaz:

```text
STATUS
✓ Potvrđen

DOSTUPNE AKCIJE
[Pacijent je stigao]
[Označi kao završen]
[Označi "nije došao"]
```

Akcije su uslovne.

Primjeri:

Ako nije confirmed:
```text
[Potvrdi termin]
```

Ako nije arrived:
```text
[Pacijent je stigao]
```

Ako je terminalan:
```text
Završen
```
bez povratnih statusnih akcija.

Odvojene operativne akcije:
```text
[Uredi termin]
[Pomjeri termin]
[Otkaži termin]
```

`Izbriši` još NE postoji u ovoj fazi.

## C.4 Context menu

Desni klik daje samo relevantne akcije.

Primjer aktivnog termina:

```text
Otvori detalje
────────────────
Potvrdi termin          # samo ako nije potvrđen
Pacijent je stigao      # samo ako nije stigao
Označi kao završen
Označi "nije došao"
────────────────
Uredi termin
Pomjeri termin
────────────────
Otkaži termin
```

Terminalni termin:
- `Otvori detalje`;
- bez besmislenih statusnih tranzicija.

Ne nuditi `Izbriši` prije Faze F.

## C.5 Arhitektura

Preferirati signal:

```python
appointment_action_requested = Signal(int, str)
```

MainWindow/controller:
- prima akciju;
- poziva service;
- refreshuje scheduler;
- refreshuje desni panel;
- refreshuje statusni summary.

Ne duplirati business logic u WeekView.

## C.6 Pomjeri termin

Stilizovani modal:

```text
Trenutno:
19.08.2026. 09:00–10:30

Novi datum *
Novo vrijeme *
Trajanje

[Odustani] [Pomjeri termin]
```

Poziva postojeći `move`.

Overlap:
- inline error;
- modal ostaje otvoren.

Drag & drop i dalje ostaje kao brži način.

## C.7 Otkaži termin

Poseban modal:

```text
Otkaži termin

Radovan Stojanović
19.08.2026. · 09:00–10:30

Otkazani termin ostaje sačuvan u istoriji.

[Odustani] [Otkaži termin]
```

NEMA razloga otkazivanja:
- trenutna šema nema gdje da ga sačuva;
- mockup sa razlogom nije obavezujući.

Poziva postojeći `cancel`.

## C.8 Statusni summary

NE UKLANJATI.

Nakon:
- confirm;
- arrived;
- completed;
- no-show;
- cancel;

summary se mora osvježiti.

Vizuelno ne smije djelovati kao klikabilni filter.

## C.9 Testovi

- lijevi klik na appointment emituje ID;
- prazan klik i dalje radi;
- context actions su status-aware;
- completed/no-show/cancel refreshuju UI;
- details nema all-status dropdown;
- terminalni statusi nemaju povratne akcije;
- move čuva duration;
- overlap na move radi;
- cancel ostavlja zapis;
- status summary se osvježava.

## C.10 Definition of Done

- [ ] lijevi klik = details;
- [ ] desni klik = brze akcije;
- [ ] drag = move;
- [ ] details koristi conditional status actions;
- [ ] cancel radi;
- [ ] hard delete još nije uveden;
- [ ] status summary ostaje i radi.

**STOP / REVIEW C**

---

# FAZA D — Online zahtjevi + desni operativni panel

**Risk:** MEDIUM  
**Zavisnost:** B (BaseDialog), preporučeno C  
**Cilj:** zamijeniti generički ConfirmationDialog i pojednostaviti desni panel.

## D.1 Putanje

```text
desktop/views/requests_panel.py
desktop/views/dialogs/process_request.py
desktop/views/main_window.py      # samo wiring ako treba
tests/test_gui/test_requests_panel.py
tests/test_gui/test_process_request_dialog.py
agent_reports/**
```

## D.2 `Potvrdi` -> `Obradi`

U request kartici koristiti jednu primarnu akciju:

```text
Obradi
```

Ne nuditi `Potvrdi | Odbij` kao dva mala dugmeta na kartici.

## D.3 `ProcessRequestDialog`

Read-only:
- pacijent;
- telefon;
- email ako postoji;
- željeni datum.

Input:
- doktor;
- vrijeme;
- usluga.

Footer:
```text
[Odbij zahtjev] [Potvrdi termin]
```

## D.4 Vrijeme — zaključana odluka

NE praviti lažne slot button-e.

Ako ne postoji pravi availability service:

```text
QTimeEdit
```

Ako tokom implementacije agent pronađe postojeći stvarni servis koji pouzdano vraća slobodne slotove:
- dokumentovati ga;
- koristiti ga samo ako ne širi scope;
- inače ostati na QTimeEdit.

Nema hardkodovanih:

```text
09:00 09:30 10:00
```

koji izgledaju kao provjerena dostupnost.

## D.5 Desni panel

Smanjiti prazne kartice.

Cilj:

```text
DANAS

Novi zahtjevi       0
Čekaju potvrdu      0
Otkazani danas      0

SLJEDEĆE

Sve je obrađeno.
```

Kada postoje zahtjevi:
- konkretna stavka;
- ime;
- datum;
- `Obradi`.

Ne izmišljati `Sljedeći slobodan termin` ako funkcionalnost ne postoji.

## D.6 Testovi

- `Obradi` postoji;
- generički ConfirmationDialog nije u glavnom toku;
- process dialog koristi doctor/time/service;
- bez lažnih slot buttona ako nema availability servisa;
- reject radi;
- confirm radi;
- overlap/error ne ruši UI;
- empty state nije četiri puta `Nema stavki`.

## D.7 Definition of Done

- [ ] online zahtjev ima jedan jasan workflow;
- [ ] doctor/time/service se određuju u modalu;
- [ ] nema lažne dostupnosti;
- [ ] panel je kompaktniji i operativniji.

**STOP / REVIEW D**

---

# FAZA E — `Dan / Sedmica` i scheduler cleanup

**Risk:** MEDIUM  
**Zavisnosti:** C  
**Cilj:** dovršiti dva jasna scheduler prikaza bez miješanja sa statusnim summaryjem.

## E.1 Putanje

```text
desktop/views/main_window.py
desktop/views/week_view.py
desktop/views/day_view.py        # novi, ako je čistije
desktop/views/widgets/**         # samo stvarno reusable dijelovi
tests/test_gui/test_main_window.py
tests/test_gui/test_week_view.py
tests/test_gui/test_day_view.py
agent_reports/**
```

## E.2 Sedmica

Zadržati postojeću logiku:
- dani kao kolone;
- filter doktora;
- pastelne doctor kartice;
- status;
- click/context/drag iz Faze C.

## E.3 Dan

Implementirati:
- izabrani datum;
- doktori kao kolone;
- vrijeme vertikalno;
- isti appointment card mentalni model;
- isti details/context action behavior.

Ako reuse sa WeekView vodi u mega-widget i povećava kompleksnost:
- napraviti zaseban `DayView`;
- dijeliti samo male stabilne helpere.

## E.4 Ukloniti nejasno

Ako `Dan / Sedmica` sada potpuno pokrivaju namjeru:

```text
Po doktoru / Paralelno
```

ukloniti.

## E.5 Statusni summary

OSTAJE.

Ova faza ga ne uklanja.

Mora biti zajednički informativni element i za Dan i za Sedmicu.

## E.6 Testovi

- Dan je enabled;
- Dan prikazuje doktore kao kolone;
- Sedmica i dalje radi;
- filter doktora ne regresira;
- click/context/drag ponašanje je konzistentno;
- status summary ostaje;
- `Po doktoru / Paralelno` uklonjeno ako je redundantno.

## E.7 Definition of Done

- [ ] Dan radi;
- [ ] Sedmica radi;
- [ ] nema trećeg nejasnog view moda;
- [ ] interakcije su iste u oba prikaza;
- [ ] status summary je sačuvan.

**STOP / REVIEW E**

---

# FAZA F — Hard delete termina

**Risk:** HIGH  
**Zavisnosti:** A + C  
**Cilj:** omogućiti trajno brisanje isključivo greškom kreiranog termina.

Ovo je NAMJERNO zaseban task.

## F.1 Review pravilo

Prije implementacije:
- zaseban Task Contract;
- eksplicitna potvrda scope-a;
- pojačan review prema projektnim pravilima;
- human approval prije merge-a.

Ako `CLAUDE.md` zahtijeva dva reviewera za HIGH, poštovati to.

## F.2 Putanje

```text
src/dentaland/services/booking.py
desktop/views/dialogs/delete_appointment.py
desktop/views/appointment_details.py ili odgovarajuća stvarna putanja
desktop/views/week_view.py        # samo context action ako se uvodi
desktop/views/main_window.py      # wiring
tests/test_services.py
tests/test_gui/**
agent_reports/**
```

Ne dirati:
```text
models.py
migrations/**
```

## F.3 Service

Dodati:

```python
delete(appt_id) -> None
```

Prije implementacije provjeriti:
- FK veze;
- cascade ponašanje;
- da li termin referencira nešto što bi delete mogao neočekivano ukloniti;
- testirati na realnoj test bazi.

Ako se pokaže da hard delete ima šire posljedice:
**STOP** i eskalirati, ne improvizovati.

## F.4 UI

`Izbriši termin` se pojavljuje:
- u Detalji termina;
- eventualno u context menu, ali vizuelno odvojeno na dnu.

Modal:

```text
Izbrisati termin?

Ova radnja trajno uklanja termin:

Radovan Stojanović
19.08.2026. · 09:00–10:30

Ako pacijent samo otkazuje termin,
koristite "Otkaži termin".

[Odustani] [Izbriši termin]
```

Pravila:
- full red destructive button;
- nije default;
- Enter ne aktivira delete;
- jasno razlikovati od cancel;
- nakon delete refresh svih relevantnih prikaza.

## F.5 Testovi

- delete uklanja tačno jedan termin;
- pogrešan ID ima kontrolisano ponašanje;
- nema neočekivanog cascade gubitka;
- cancel i delete imaju različite rezultate;
- destructive button nije default;
- UI traži eksplicitnu potvrdu.

## F.6 Definition of Done

- [ ] hard delete je izolovan;
- [ ] FK/cascade posljedice provjerene;
- [ ] cancel ostaje preferirani normalni workflow;
- [ ] HIGH review završen;
- [ ] human approval prije merge-a.

**STOP / REVIEW F**

---

# 3. Zajednički vizuelni standard

Sve faze koje dodaju dialog koriste isti sistem.

## Boje

Koristiti postojeće vrijednosti iz aplikacije kao source of truth.

Ne uvoditi novu približnu teal ako već postoji theme konstanta.

Princip:
- white surface;
- Dentaland teal primary;
- dark navy text;
- soft gray/blue border;
- pastel doctor colors;
- red samo za destructive akcije.

## Kontrole

- input 38–42 px;
- label iznad;
- focus teal;
- radius 6–8 px;
- modal radius 10–12 px;
- primary teal;
- secondary white/outline;
- destructive red.

## Ikone

SVG / postojeći icon helper.

Bez emoji u finalnom UI-ju.

---

# 4. Globalne regresije koje se ne smiju pojaviti

Sve faze zajedno moraju sačuvati:

- doctor filter;
- pastelne doctor boje;
- status prikaz na kartici;
- statusni live summary;
- half-hour klik;
- postojeće radno vrijeme;
- postojeće dane rada prikazane u scheduleru;
- blockout/time-off;
- drag & drop;
- overlap zaštitu;
- štampu;
- automatski refresh web zahtjeva;
- sidebar routing;
- postojeći backup/web tok;
- nula SQLAlchemy importa u `desktop/views/`.

---

# 5. Van scope-a svih 6 faza

Ne implementirati:

- DB migracije;
- nove DB kolone;
- razlog otkazivanja;
- audit log;
- restore cancelled;
- reopen completed/no-show;
- medicinski karton;
- treatment plan;
- račune;
- CRM;
- recurring appointments;
- multi-tenancy;
- novi web booking model;
- lažni availability engine;
- redizajn print dokumenta.

Ako bilo koja faza utvrdi da nešto od ovoga postaje nužno:
**STOP i novi plan**, ne tiho širiti scope.

---

# 6. Redoslijed realizacije

Tačan redoslijed:

```text
A — Service edit/status capabilities
        ↓
B — BaseDialog + Novi/Uredi termin
        ↓
C — Detalji + click/context + move/cancel
        ↓
D — Online zahtjevi + desni panel
        ↓
E — Dan/Sedmica
        ↓
F — Hard delete (HIGH, zasebno)
```

Faza F može biti odgođena bez blokiranja A–E.

To je namjerno.

---

# 7. Review checkpoints

Nakon svake faze reviewer mora odgovoriti na tri pitanja:

1. Da li implementacija radi ono što faza traži?
2. Da li je agent proširio scope bez odobrenja?
3. Da li je uvedena regresija u scheduler/service sloju?

Ako odgovor na 2 ili 3 nije čist:
- ne nastavljati na sljedeću fazu.

---

# 8. Finalni end-to-end QA nakon A–E

Prije hard delete faze korisnik mora moći:

1. kliknuti prazan slot;
2. dobiti novi stilizovani editor;
3. odabrati doktora u istom modalu;
4. odabrati uslugu;
5. dobiti predloženo trajanje;
6. sačuvati;
7. kliknuti termin;
8. dobiti Detalji termina;
9. potvrditi termin;
10. označiti pacijenta kao stiglog;
11. urediti termin;
12. promijeniti doktora;
13. pomjeriti termin;
14. završiti termin;
15. kreirati drugi termin;
16. otkazati ga i zadržati u istoriji;
17. obraditi web zahtjev;
18. izabrati doktora;
19. ručno odrediti vrijeme bez lažnog availability prikaza;
20. potvrditi zahtjev;
21. koristiti Dan prikaz;
22. vratiti se na Sedmicu;
23. i dalje vidjeti živi statusni summary;
24. koristiti štampu i doctor filter bez regresije.

Tek nakon toga razmatrati Fazu F.

---

# 9. Finalni QA nakon Faze F

Dodatno:

25. kreirati testni termin greškom;
26. otvoriti detalje;
27. izabrati `Izbriši termin`;
28. dobiti jasan destructive modal;
29. potvrditi;
30. termin mora nestati;
31. drugi otkazani termin mora i dalje postojati u istoriji.

Time se praktično potvrđuje razlika:

```text
OTKAŽI = istorijski zapis ostaje
IZBRIŠI = trajno uklanjanje
```

---

# 10. Evidence standard za svaku fazu

Svaka faza dobija svoj fajl:

```text
agent_reports/DENT-DESKTOP-A-*.md
agent_reports/DENT-DESKTOP-B-*.md
...
```

Minimalno:
- cilj faze;
- izmijenjeni fajlovi;
- šta je implementirano;
- šta namjerno nije implementirano;
- test komande;
- rezultati;
- ruff rezultat;
- screenshotovi ako je GUI faza;
- poznate LOW napomene;
- potvrda da forbidden putanje nisu dirane.

Za Fazu F dodatno:
- FK/cascade analiza;
- HIGH review evidence;
- human approval evidence prema projektnom procesu.

---

# 11. Konačna namjera

Ovaj redizajn nije jedan veliki "napravi sve" prompt.

To je niz kontrolisanih promjena:

```text
SERVICE TEMELJ
    ↓
EDITOR
    ↓
RAD SA POSTOJEĆIM TERMINOM
    ↓
ONLINE ZAHTJEVI
    ↓
DAN/SEDMICA
    ↓
POSEBNO ODOBREN HARD DELETE
```

Time dobijamo:
- manji blast radius;
- lakši review;
- lakši rollback;
- jasne granice odgovornosti agenata;
- manje šanse da agent implementira mockup kao funkciju koju backend zapravo nema;
- mogućnost da se A–E završe i koriste čak i ako se hard delete odluči odgoditi.

Najvažnija UX pravila ostaju:

```text
LIJEVI KLIK = DETALJI
DESNI KLIK = BRZE AKCIJE
DRAG = POMJERANJE
STATUS = USLOVNE AKCIJE, NE SLOBODAN DROPDOWN
ONLINE VRIJEME = RUČNI IZBOR DOK NEMA PRAVOG AVAILABILITY SERVISA
STATUSNI SUMMARY = OSTAJE
DELETE = ODVOJEN HIGH-RISK TASK
```
