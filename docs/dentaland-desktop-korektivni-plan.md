# Dentaland Desktop — korektivni plan nakon pregleda trenutnog `main` stanja

**Datum pregleda:** 21.08.2026.  
**Repo:** `Rade69/Dentaland`  
**Namjena:** instrukcije za agenta koji treba popraviti preostale funkcionalne i UX nedosljednosti nakon implementacije glavnog scheduler redizajna.

## 0. Kontekst

Glavni scheduler workflow je već implementiran i ne treba ga graditi ponovo.

Već postoje:
- unified `Novi/Uredi termin` editor;
- `Detalji termina`;
- lijevi klik na termin;
- desni context menu;
- statusne akcije;
- `Pomjeri termin`;
- `Otkaži termin`;
- hard delete;
- `Dan / Sedmica`;
- online `Obradi zahtjev`;
- zasebni `RequestsPage`;
- Blockout;
- Postavke;
- statusni live summary;
- testovi i CI.

Ovo je korektivni/polish paket, ne novi feature-redizajn.

---

# 1. PRIORITET 1 — DayView mora prikazivati blockout/time-off

## Problem

`WeekView` prikazuje blokade i odsustva, ali `DayView` trenutno učitava samo termine.

To stvara opasnu nedosljednost:

```text
Sedmica:
Dr Zorka 10:00–12:00 = BLOKIRANO

Dan:
Dr Zorka 10:00–12:00 = izgleda slobodno
```

To može navesti osoblje da pokuša zakazati termin kada doktor nije dostupan.

## Fajlovi

```text
desktop/views/day_view.py
src/dentaland/services/booking.py     # samo ako nedostaje reusable read helper
tests/test_gui/test_day_view.py
```

## Šta uraditi

DayView mora koristiti isti izvor blokada kao WeekView.

Prikazati:
- `TimeOff`;
- split-shift/pauze ako ih WeekView prikazuje kroz postojeći servisni helper.

Za izabrani dan:
- dohvatiti relevantne blokade;
- mapirati ih na doctor kolonu;
- prikazati kao neklikabilan blok;
- slot unutar blokade ne smije emitovati `slot_selected`.

Ne duplirati business logiku ako već postoje:
- `time_off_for_week(...)`;
- `breaks_for_week(...)`;
- `CalendarBlockDTO`.

Dozvoljeno je napraviti mali helper tipa `calendar_blocks_for_day(day)` samo ako je to čišće od filtriranja postojećih week helpera.

## Acceptance

- [ ] blockout vidljiv u DayView;
- [ ] pauza/split-shift vidljiva ako je već podržana u WeekView;
- [ ] blokiran slot se ne može kliknuti kao slobodan;
- [ ] status/appointment rendering nije regresiran.

---

# 2. PRIORITET 2 — Popraviti edit trajanja termina

## Problem

U `AppointmentEditorDialog` edit mode prvo prefilluje stvarno trajanje postojećeg termina, ali kasnije konstruktor može primijeniti default trajanje usluge i prepisati postojeće ručno trajanje.

Primjer:

```text
Usluga default: 60 min
Postojeći termin: 90 min
Otvori "Uredi termin"
Ne smije se vratiti na 60 min
```

## Fajlovi

```text
desktop/views/dialogs/appointment_editor.py
tests/test_gui/test_appointment_dialog.py
```

## Pravilo

### Create mode
- početno trajanje dolazi iz odabrane usluge;
- promjena usluge može ažurirati trajanje.

### Edit mode
- početno trajanje mora biti stvarno postojeće trajanje termina;
- konstruktor ga ne smije odmah prepisati defaultom usluge;
- tek ako korisnik naknadno promijeni uslugu, može se predložiti novo default trajanje.

Najjednostavnije:
- connect na `currentIndexChanged` nakon `_prefill()`;
- ili ne pozivati `_apply_service_duration(...)` kod edit moda.

## Obavezni regression test

```text
service "Plomba" default = 60
existing appointment duration = 90
edit dialog duration == 90
```

i dodatno:

```text
nakon ručne promjene service combo-a
duration se može promijeniti na default nove usluge
```

---

# 3. PRIORITET 3 — Day header i doctor filter ponašanje

## Problem A — datum

`_update_range_label()` trenutno prikazuje sedmični raspon i kada je aktivan `Dan`.

U Day modu treba prikazati konkretan datum, npr.:

```text
Petak, 21. avgust 2026.
```

## Problem B — doctor filter

Doctor tabs trenutno mijenjaju samo:

```python
self.week_view.set_filter(doctor_id)
```

DayView i dalje prikazuje sve doktore.

## Preporučena odluka

### Sedmica
- doctor tabs vidljivi;
- `Svi doktori / Ljubo / Zorka / Ana`.

### Dan
- doctor tabs sakriti ili disable-ovati;
- doktori ostaju kolone.

Ne implementirati filtriranje Day kolona ako nije stvarno potrebno.

## Fajlovi

```text
desktop/views/main_window.py
tests/test_gui/test_main_window.py
```

## Acceptance

- [ ] Day prikazuje konkretan datum;
- [ ] Sedmica prikazuje sedmični raspon;
- [ ] doctor filter je aktivan samo gdje ima smisla;
- [ ] prebacivanje Dan/Sedmica pravilno osvježava header.

---

# 4. PRIORITET 4 — Razdvojiti `NO_SHOW` i `CANCELLED` u UI statusima

## Problem

Trenutno `CANCELLED` i `NO_SHOW` mapiraju na isti vizuelni status:

```text
Otkazan / Nije došao
```

Poslovno to nisu ista stanja.

## Fajlovi

```text
desktop/views/week_view.py
desktop/views/day_view.py
desktop/views/dialogs/appointment_details.py
desktop/views/main_window.py
tests/test_gui/test_week_view.py
tests/test_gui/test_day_view.py
tests/test_gui/test_appointment_details_dialog.py
tests/test_gui/test_main_window.py
```

## Novo mapiranje

Preporuka:

```python
"cancelled": ("✗", RED, "Otkazan")
"no_show": ("!", ORANGE_OR_RED_VARIANT, "Nije došao")
```

`_status_key()`:

```text
CANCELLED -> cancelled
NO_SHOW   -> no_show
COMPLETED -> completed
arrived   -> arrived
confirmed -> confirmed
else      -> waiting
```

## Status summary

Live summary treba odvojeno prikazivati:

```text
Potvrđen (x)
Čeka potvrdu (x)
Stigao (x)
Završen (x)
Nije došao (x)
Otkazan (x)
```

Ako nema dovoljno širine:
- smanjiti spacing/font;
- dozvoliti wrap u 2 reda;
- ne spajati statuse samo zbog prostora.

## Acceptance

- [ ] no-show i cancelled imaju odvojene countove;
- [ ] kartice imaju različitu oznaku;
- [ ] details modal pokazuje tačno stanje;
- [ ] postojeći status action workflow nije promijenjen.

---

# 5. PRIORITET 5 — Ne gutati `ValueError` bez feedbacka

## Problem

`MainWindow` trenutno na više mjesta radi:

```python
with suppress(ValueError):
    method(...)
```

Ako operacija ne uspije, korisnik ne dobije objašnjenje.

## Fajlovi

```text
desktop/views/main_window.py
desktop/views/dialogs/base_dialog.py       # samo ako treba reusable helper
tests/test_gui/test_main_window.py
```

## Šta uraditi

Za očekivane poslovne greške:
- ne rušiti aplikaciju;
- ne ignorisati grešku;
- prikazati jasan feedback.

Primjeri:

```text
Termin više nije moguće označiti kao stigao jer je već otkazan.
```

```text
Termin nije pronađen. Raspored će biti osvježen.
```

```text
Ovu radnju nije moguće izvršiti nad završenim terminom.
```

Ne prikazivati traceback.

Ako postojeći service `ValueError` već ima čistu user-facing poruku, može se koristiti.

## Acceptance

- [ ] nijedna glavna appointment akcija ne guta `ValueError` u tišini;
- [ ] UI ostaje stabilan;
- [ ] nakon greške scheduler se po potrebi refreshuje.

---

# 6. PRIORITET 6 — DayView drag & drop

## Status

Korisno, ali nije blokirajuće kao Prioriteti 1–5.

## Problem

Mentalni model nije potpuno isti:

```text
Sedmica: drag radi
Dan: drag ne radi
```

## Cilj

Ako implementacija ostaje čista:
- omogućiti drag appointmenta u DayView;
- između doctor kolona = promjena doktora + vremena.

## Arhitektonska napomena

Trenutni `move()` mijenja samo vrijeme i koristi doktora postojećeg termina.

Ako DayView drag između kolona mijenja doktora, ne hackovati `move()`.

Koristiti postojeći `update()` ili jasan orkestrirani tok:

```text
same doctor column -> move()
different doctor column -> update(... doctor_id=new_doctor ...)
```

Overlap mora provjeriti ciljnog doktora.

Ako task postane preširok:
- u prvoj iteraciji podržati drag samo unutar iste doctor kolone;
- između doktora ostaviti `Uredi termin`.

## Fajlovi

```text
desktop/views/day_view.py
desktop/views/main_window.py
tests/test_gui/test_day_view.py
tests/test_gui/test_main_window.py
```

---

# 7. PRIORITET 7 — Vizuelno uskladiti Settings i Blockout

## Status

LOW/MEDIUM polish.

## Problem

Glavni appointment workflow koristi `BaseDialog`, ali pomoćni dijelovi još imaju:
- native `QDialog`;
- `QDialogButtonBox(OK/Cancel)`;
- `QMessageBox`.

To vizuelno djeluje kao drugi proizvod.

## Fajlovi

```text
desktop/views/settings_panel.py
desktop/views/blockout_panel.py
desktop/views/dialogs/base_dialog.py
desktop/views/dialogs/**
tests/test_gui/test_settings_panel.py
tests/test_gui/test_blockout_panel.py
```

## Settings

Redizajnirati:

```text
ServiceDialog
IntervalDialog
```

da koriste `BaseDialog`.

Akcije:

```text
Odustani
Sačuvaj
```

umjesto:

```text
OK
Cancel
```

Za greške koristiti inline error gdje je praktično.

## Blockout

Brisanje blokade više ne treba generic:

```python
QMessageBox.question(...)
```

Napraviti mali Dentaland destructive confirm dialog.

---

# 8. Dodatna provjera desnog dashboard panela

Nije hitno, ali nakon gore navedenih popravki razmotriti kompaktniji summary.

Trenutno postoje:

```text
Novi zahtjevi
Čekaju potvrdu
Otkazani danas
```

Kada su prazni, neki prikazuju `Nema stavki`.

Pošto postoji zaseban `RequestsPage`, kasnije razmotriti:
- manje praznog prostora;
- više summary pristup;
- bez dupliranja onoga što radi RequestsPage.

Ne raditi ovo prije Prioriteta 1–5.

---

# 9. Regresije koje se ne smiju pojaviti

Obavezno sačuvati:
- unified appointment editor;
- details modal;
- conditional status actions;
- context menu;
- hard delete/cancel razliku;
- status live summary;
- doctor pastel boje;
- WeekView drag & drop;
- online `Obradi zahtjev`;
- RequestsPage;
- Blockout CRUD;
- Settings CRUD;
- štampu;
- auto-refresh;
- CI;
- service/GUI separaciju;
- nula SQLAlchemy importa u `desktop/views/`.

---

# 10. Preporučeni task split

## FIX-01 — DayView correctness
Sadrži:
- blockout/time-off;
- Day header;
- doctor filter behavior.

**Risk:** MEDIUM

## FIX-02 — Appointment editor duration regression
Sadrži:
- edit duration bug;
- testove.

**Risk:** LOW

## FIX-03 — Status semantics
Sadrži:
- NO_SHOW/CANCELLED razdvajanje;
- summary;
- cards;
- details.

**Risk:** MEDIUM

## FIX-04 — Error feedback
Sadrži:
- uklanjanje `suppress(ValueError)`;
- user-facing feedback;
- testove.

**Risk:** LOW/MEDIUM

## FIX-05 — DayView drag & drop

**Risk:** MEDIUM

## FIX-06 — Secondary UI visual polish
Sadrži:
- Settings dialogs;
- Blockout confirm;
- BaseDialog reuse.

**Risk:** LOW

---

# 11. Redoslijed

Preporučeno:

```text
FIX-01
FIX-02
FIX-03
FIX-04
FIX-05
FIX-06
```

Ako želite prvo zatvoriti mali bug radi brzog dobitka:

```text
FIX-02
FIX-01
FIX-03
FIX-04
FIX-05
FIX-06
```

---

# 12. Finalni QA scenario

1. Kreirati blockout za Zorku 10:00–12:00.
2. Sedmica — blokada se vidi.
3. Dan — blokada se vidi i tamo.
4. Klik blokiranog Day slota ne otvara Novi termin.
5. Kreirati termin usluge default 60 min.
6. Urediti trajanje na 90 min.
7. Ponovo otvoriti edit — i dalje 90 min.
8. Promijeniti uslugu — tada se može predložiti novo default trajanje.
9. Otvoriti Dan — header prikazuje konkretan datum.
10. Doctor filter ne zbunjuje korisnika u Day modu.
11. Označiti jedan termin `NO_SHOW`.
12. Otkazati drugi.
13. Summary prikazuje odvojeno `Nije došao` i `Otkazan`.
14. Pokušati nevažeću statusnu akciju — korisnik dobija poruku.
15. WeekView drag i dalje radi.
16. Ako FIX-05 postoji — Day drag radi po definisanom pravilu.
17. Settings i Blockout dijalozi vizuelno pripadaju istoj aplikaciji.

---

# 13. Definition of Done

- [ ] DayView ne prikazuje blokirano vrijeme kao slobodno;
- [ ] edit ne gubi ručno trajanje;
- [ ] Day header je tačan;
- [ ] doctor filter nema kontradiktorno ponašanje;
- [ ] `NO_SHOW` i `CANCELLED` su odvojeni u UI-ju;
- [ ] appointment akcije ne gutaju greške;
- [ ] svi novi testovi prolaze;
- [ ] postojeći test baseline nije regresiran;
- [ ] Ruff čist;
- [ ] mypy čist;
- [ ] nema SQLAlchemy importa u `desktop/views`;
- [ ] nema novih migracija za ove popravke.

---

# 14. Ključna napomena agentu

Ne pokušavaj ponovo redizajnirati Dentaland.

Glavni UX model je već prihvaćen.

Ovaj paket služi da ukloni:
- nekonzistentnosti;
- jedan stvarni DayView correctness problem;
- jedan edit regression bug;
- statusnu semantičku grešku;
- tiho gutanje grešaka;
- preostali vizuelni dug.

Ako tokom implementacije naiđeš na novu ideju koja širi scope, zabilježi je kao `OUT_OF_SCOPE_FINDING` i ne implementiraj bez odobrenja.
