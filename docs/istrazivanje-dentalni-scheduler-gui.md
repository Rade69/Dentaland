# Istraživanje GUI obrazaca za dentalni raspored

**Datum istraživanja:** 17.08.2026.\
**Namjena:** referentni dokument za Claudeov nezavisni pregled prije
redizajna desktop aplikacije.

## 1. Cilj

Cilj nije kopirati postojeći dentalni softver, nego provjeriti kako
zreli proizvodi rješavaju svakodnevni operativni rad: raspored, više
doktora, promjene termina, status pacijenta, blokirano vrijeme i dolazne
zahtjeve.

Pregledani su Open Dental, Curve Dental, NexHealth i djelimično Dentrix.
Najviše konkretnih javnih UI/workflow podataka pronađeno je u službenoj
dokumentaciji Open Dental, Curve Dental i NexHealth.

## 2. Glavni zaključak

Postojeći mockup je vizuelno čist, ali djelimično organizovan kao SaaS
dashboard. Dentalni scheduler je prije svega **operativni alat**.
Korisniku je važnije da bez dodatnih klikova vidi raspored, doktore,
statuse, blokade i zahtjeve nego procente i opštu statistiku.

Preporuka: zadržati čist izgled i teal paletu, ali povećati funkcionalnu
gustoću centralnog rasporeda i desni panel pretvoriti prvenstveno u
operativni inbox.

## 3. Open Dental

Open Dental koristi **Appointments Module** kao centralno mjesto za
pregled, zakazivanje i upravljanje terminima.

Pronađeni obrasci: - prilagodljivi Appointment Views; - izbor
operatorija i providera; - day/week pregled; - Confirmation, Recall i
Unscheduled liste; - Waiting Room; - brzo štampanje; - Pinboard za
termine koji tek treba da se smjeste u raspored; - konfigurabilne
informacije unutar kartice termina; - vremenski inkrementi od 5/10/15
minuta.

Posebno je bitan provider/operatory koncept: raspored se može
organizovati prema doktorima i fizičkim radnim mjestima, ne samo prema
datumu.

**Šta vrijedi prenijeti:** 1. Raspored je primarni ekran. 2. Prikaz
doktora mora biti lako promjenjiv. 3. Statusi i operativne liste trebaju
biti dostupni uz raspored. 4. Nezakazani/nepotvrđeni zahtjevi prirodno
pripadaju uz scheduler. 5. Dan/Sedmica i doktor mijenjaju se bez
napuštanja ekrana.

### Izvori --- Open Dental

-   https://www.opendental.com/site/0_appointments.html
-   https://www.opendental.com/manual/appointmentviewsetup.html
-   https://www.opendental.com/manual/schedulesetupexamples.html
-   https://www.opendental.com/manual/operatories.html
-   https://www.opendental.com/manual/providers.html
-   https://www.opendental.com/manual/odtouchappts.html

## 4. Curve Dental

Curve koristi Scheduler kao centralni operativni prikaz i **Sidekick**
panel uz glavni radni prostor. Sidekick može držati informacije i
elemente koji se zatim mogu prevući na Scheduler.

Curve omogućava da osnovna boja termina predstavlja **Appointment Type
ili Provider**. Status termina može imati odvojenu statusnu traku/boju.
Dokumentacija za check-in pokazuje promjenu statusne boje i Appointment
Summary na hoveru.

SnapShot prikaz koristi kratke vizuelne indikatore za status, providera,
vrijeme i druge operativne informacije.

**Šta vrijedi prenijeti:** 1. Boja kartice može predstavljati doktora.
2. Status treba imati odvojen indikator. 3. Desni panel može služiti kao
Sidekick/inbox. 4. Hover/klik može dati kratki sažetak prije pune forme.
5. Drag-and-drop je prirodan dio schedulera.

### Izvori --- Curve Dental

-   https://curvedental.zendesk.com/hc/en-us/articles/50388751420691-Navigating-the-Sidekick
-   https://curvedental.zendesk.com/hc/en-us/articles/50403864709523-Checking-In-an-Appointment-and-Undoing-a-Check-In
-   https://curvedental.zendesk.com/hc/en-us/articles/50984215211667-Editing-Appointment-Color-Settings-and-Appointment-Printout-Settings
-   https://curvedental.zendesk.com/hc/en-us/articles/49762048361235-How-do-I-Change-the-Default-Appointment-Color
-   https://curvedental.zendesk.com/hc/en-us/articles/50403777447059-Understanding-the-SnapShot-Report

## 5. NexHealth

NexHealth je scheduling/integration platforma, ali dokumentacija dobro
pokazuje logiku dostupnosti.

Raspoloživost izvodi iz: 1. radnog vremena providera; 2. calendar
unavailability/blockout zapisa; 3. appointment-type pravila; 4.
operatorija.

**Calendar unavailability** je posebno koristan obrazac. Pauza, sastanak
ili drugo nedostupno vrijeme postoji kao stvaran blok i uklanja vrijeme
iz dostupnih slotova. Dokumentacija navodi da Open Dental
blockouts/holidays i Dentrix event blocks mogu biti tretirani kao
calendar unavailability.

**Preporuka:** nedostupnost ne prikazivati samo kao prazninu.
Primjeri: - `12:00–13:00 — Pauza` - `Dr Zorka — godišnji odmor` -
`Dr Ljubo — van ordinacije` - `Sastanak osoblja`

### Izvor --- NexHealth

-   https://docs.nexhealth.com/docs/scheduling-configuration-guide

## 6. Dentrix

Dentrix je relevantan proizvod, ali u ovom prolazu nisam našao jednako
detaljne javne službene UI izvore kao za Open Dental i Curve. NexHealth
dokumentacija potvrđuje Dentrix event blocks kao calendar
unavailability.

**Za Claude:** prije detaljnih Dentrix UI zaključaka dodatno provjeriti
aktuelnu Dentrix Appointment Book dokumentaciju/screenshotove. Ne treba
pripisivati Dentrixu detalje koje ovdje nismo direktno potvrdili.

## 7. Analiza postojećeg mockupa

### Zadržati

-   veliki centralni sedmični kalendar;
-   teal vizuelni identitet;
-   `Danas` + prethodna/sljedeća sedmica;
-   `Dan / Sedmica`;
-   `+ Novi termin`;
-   drag-and-drop;
-   boje po doktoru;
-   panel `Novi zahtjevi`;
-   štampu.

### Preispitati navigaciju

`Raspored`, `Termini` i `Kalendar` su semantički previše slični.

Predlog: - Raspored - Novi zahtjevi - Pacijenti - Izvještaji - Postavke

### Preispitati desni panel

Stalni `Brzi pregled` sa ukupnim brojem termina i procentom popunjenosti
nije dovoljno vrijedan za toliko prostora.

Bolja namjena: - Novi zahtjevi - Čekaju potvrdu - Otkazani / za ponovno
zakazivanje - eventualno sljedeći slobodan termin

Statistika ide u `Izvještaji`.

## 8. Prikaz doktora

Zadržati: `Svi doktori | Dr Ljubo | Dr Zorka | Dr Ana`

Vrijedi razmotriti dva režima:

**Sedmica:** kolone = dani, boja kartice = doktor.

**Dan:** kolone = doktori, vertikalna osa = vrijeme.

Dnevni prikaz po doktorima može recepciji mnogo brže pokazati ko je
slobodan u konkretnom trenutku.

## 9. Kartica termina

Kompaktan primjer:

``` text
Nikola Jovanović
13:00–13:45
Dr Zorka
● Potvrđen
```

Boja pozadine može predstavljati doktora; mali badge/traka predstavlja
status. Jedna boja ne treba istovremeno predstavljati i doktora i
status.

## 10. Interakcija

**Jedan klik:** mali detail popover/bočni detalj sa pacijentom,
vremenom, doktorom, telefonom, statusom i akcijama `Uredi` / `Otkaži`.

**Double-click / Uredi:** puna forma.

**Drag-and-drop:** direktno pomjeranje termina.

## 11. Blockout

Dodati poseban vizuelni element koji nije termin pacijenta:

``` text
12:00–13:00
PAUZA
Dr Ljubo
```

ili cjelodnevni blok `Dr Zorka — GODIŠNJI ODMOR`.

Vizuelno neutralnije od termina, npr. siva/šrafirana pozadina.

## 12. Statusi --- prijedlog za diskusiju

Ne uvoditi veliki broj statusa samo zato što ih veliki sistemi imaju.
Minimalni korisni set za razmatranje: - Čeka potvrdu - Potvrđen -
Stigao - Završen - Otkazan - Nije došao

Ovo nije zaključana specifikacija.

## 13. Predložena struktura ekrana

**Toolbar:** `Danas`, prethodna/sljedeća sedmica, datum, filter doktora,
`Dan/Sedmica`, `+ Novi termin`, `Štampa`.

**Lijevo:** Raspored, Novi zahtjevi, Pacijenti, Izvještaji, Postavke.

**Centar:** veliki scheduler kao dominantan dio aplikacije.

**Desno:** operativni inbox.

Kod javnog modela gdje pacijent bira datum, a ordinacija naknadno
određuje doktora i vrijeme, akcija **`Obradi`** može biti semantički
preciznija od prostog `Potvrdi`, jer obrada zahtjeva podrazumijeva
dodjelu doktora i tačnog vremena.

## 14. Važna projektna preporuka

Ne kopirati veliki dentalni ERP. Open Dental i Curve imaju funkcije za
treatment plans, insurance, recall, operatories, clinical charting,
production itd. Treba preuzeti njihove **provjerene interaction
patterns**, ali ne njihov scope.

Za sada držati fokus na: - rasporedu; - doktorima; - terminima; -
blockoutima; - novim online zahtjevima; - osnovnom statusu; - kontaktu
pacijenta; - štampi.

## 15. Pitanja za Claudeov nezavisni pregled

1.  Da li je za malu ordinaciju bolji sedmični prikaz po danima ili
    dnevni prikaz po doktorima kao primarni ekran?
2.  Da li oba prikaza trebaju od početka?
3.  Da li je desni stalni inbox opravdan ili je bolji badge + drawer?
4.  Koji minimalni statusi stvarno trebaju?
5.  Da li boja treba predstavljati doktora ili tip termina?
6.  Kako najjednostavnije modelovati blockout?
7.  Da li `Novi zahtjevi` treba biti stalno vidljiv ili samo kada
    postoje zahtjevi?
8.  Koje informacije moraju stati na appointment card?
9.  Da li mini-kalendar desno opravdava prostor?
10. Koje Open Dental/Curve obrasce treba namjerno odbaciti kao
    prekompleksne?

## 16. Zaključak

Najvažniji rezultat istraživanja:

> **Desktop aplikaciju treba tretirati kao scheduler sa pomoćnim
> operativnim panelom, a ne kao dashboard koji slučajno sadrži
> kalendar.**

Postojeći mockup je dobra vizuelna osnova i ne treba ga rušiti. Treba
pojednostaviti navigaciju, dati više prostora scheduleru, desni panel
pretvoriti u operativni inbox, razdvojiti doktor-boju od statusa, dodati
blockout prikaz i ozbiljno razmotriti dnevni prikaz sa doktorima kao
kolonama.
