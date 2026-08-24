# Dentaland — fazni plan arhitektonskog refaktorisanja

**Cilj:** vratiti aplikaciju na jasno i strogo načelo **View / Controller / Services** bez big-bang rewrite-a, bez nepotrebne apstrakcije i bez promjene poslovnog ponašanja osim gdje je eksplicitno označeno kao korekcija.

**Repo stanje na kojem je plan zasnovan:** `main`, 24.08.2026.  
**Baseline prije početka:** 298 pytest passed, Ruff čist, mypy čist.  
**Proces rada:** Pi i Crush implementiraju. Codex i Claude rade dva nezavisna review-a. Radovan daje finalni human approval prije merge-a.

**Napomena (Claude, 24.08.2026):** plan je nezavisno provjeren protiv stvarnog stanja `main`-a prije nego što je odobren za implementaciju — vidi sekciju 0. Sve brojke i tvrdnje u sekciji 1 su potvrđene tačne (ne pretpostavljene). Otkriveno je i nekoliko konkretnih nalaza koji nisu bili vidljivi iz same namjere plana — ugrađeni su direktno u relevantne REF-XX sekcije niže, označeni sa **"Nalaz review-a (Claude, 24.8.2026)"**.

---

# 0. Verifikacija plana protiv koda (Claude, 24.08.2026, prije starta)

Prije nego što je plan odobren za implementaciju, sljedeće tvrdnje su provjerene direktno u kodu na `main`-u (ne pretpostavljene iz prose):

- `main_window.py`: 863 linija / 35.6 KB (plan je naveo ≈34.8 KB — blizu, blag drift od 21–22.8.).
- `booking.py`: 796 linija / 31.9 KB (plan je naveo ≈31.1 KB — isto blag drift).
- Overlap duplikacija (`booking.py` + `requests.py`) je **stvarna i eksplicitno dokumentovana u kodu** — `requests.py:131-133` sadrži docstring *"Ista logika kao AppointmentService._check_overlap u booking.py — namjerno duplirana, ne dijeljena"*. Uzrok NIJE arhitektonski nemar: to je bila taktička odluka od 16.8.2026 (vidi `agent_reports/2026-08-16-DENT-007-plan.md`) da se izbjegne merge-path sudar dok su DENT-006 i DENT-007 paralelno mijenjali iste fajlove. Dobra vijest za REF-01: duplikacija je poznat, privremeni dug sa jasnim uzrokom, ne skrivena zamka.
- `day_view.py` stvarno uvozi iz `week_view.py`, i gore nego što osnovni opis sugeriše: `from desktop.views.week_view import STATUS_META, WeekView, _status_key, status_icon` — uključuje `_status_key`, **privatan simbol** (vodeći underscore) preko granice modula.
- `desktop/fake_data.py::SARAJEVO` se uvozi na **pet mjesta**, ne samo u `main_window.py`: `blockout_panel.py`, `day_view.py`, `week_view.py`, `dialogs/blockout_delete_confirm.py`, `main_window.py`.
- **Kritičan nalaz koji plan nije eksplicitno pokrivao:** `booking.py` i `requests.py` definišu DVIJE ODVOJENE `OverlapError` klase (isto ime, različita klasa):
  - `src/dentaland/services/booking.py:135` — hvata je `desktop` (preko `dentaland.services.__init__` re-eksporta, koristi je `main_window.py`/dialog kod).
  - `src/dentaland/services/requests.py:30` — hvata je `backend/main.py:172` (`except OverlapError`).

  Ovo je detaljnije razrađeno u REF-01 acceptance nižem — nije opciono, mora biti eksplicitno riješeno da se izbjegne tiha regresija (npr. 409 → 500 na backend API-ju ako se pogrešna klasa uhvati poslije objedinjavanja).

---

# 1. Zašto se refaktor radi sada

Aplikacija je funkcionalno znatno napredovala, ali originalna arhitektonska odluka je počela da erodira:

```text
VIEW
  ↓
CONTROLLER
  ↓
SERVICES
  ↓
DATABASE
```

U stvarnom kodu trenutno postoje dva glavna hotspot-a:

```text
desktop/views/main_window.py
    ≈ 34.8 KB
    View shell
    + routing
    + scheduler orchestration
    + appointment workflow
    + refresh orchestration
    + print orchestration
    + theme/QSS

src/dentaland/services/booking.py
    ≈ 31.1 KB
    appointment CRUD
    + status lifecycle
    + time-off
    + working hours
    + settings
    + pending request facade
    + overlap validation
    + calendar block generation
    + DTO mapping
```

Pored toga:
- `week_view.py` i `day_view.py` dijele presentation logiku preko importa iz jednog view-a u drugi;
- overlap pravilo postoji na više mjesta (`booking.py`, `requests.py`);
- scheduler učitava širi skup termina nego što mu je potreban;
- refresh ciklus može više puta dohvatiti iste podatke;
- `MainWindow` je postao merge-conflict hotspot za skoro svaki GUI task.

Ovaj plan ne razbija fajlove zato što su veliki. Razdvaja ih zato što su **odgovornosti pogrešno spojene**.

---

# 2. Ciljna arhitektura

Poslije refaktora struktura treba konceptualno izgledati ovako:

```text
desktop/
│
├── app.py
│
├── views/
│   ├── main_window.py
│   ├── week_view.py
│   ├── day_view.py
│   ├── requests_page.py
│   ├── settings_panel.py
│   ├── blockout_panel.py
│   └── dialogs/
│
├── controllers/
│   ├── schedule_controller.py
│   ├── appointment_controller.py
│   ├── request_controller.py
│   └── print_controller.py
│
└── presentation/
    ├── theme.py
    ├── schedule_status.py
    ├── schedule_palette.py
    ├── appointment_menu.py
    └── slot_math.py

src/dentaland/
└── services/
    ├── appointments.py
    ├── availability.py
    ├── requests.py
    ├── settings.py
    ├── notifications.py
    └── print_schedule.py
```

**Važno:** ovo je cilj odgovornosti, ne obavezna naredba da se svaki navedeni fajl mora kreirati. Ako se kroz implementaciju pokaže da dvije male cjeline prirodno pripadaju zajedno, ne praviti mikro-fajlove bez razloga.

---

# 3. Stroga pravila slojeva nakon refaktora

## 3.1 View

View smije:
- crtati UI;
- emitovati Qt signale;
- prikazati DTO/read model;
- prikazati user-facing validation/error poruku koju mu Controller proslijedi;
- imati lokalnu presentation logiku.

View NE smije:
- pozivati SQLAlchemy;
- donositi poslovnu odluku da li je termin dozvoljen;
- koordinirati više servisa;
- odlučivati status tranziciju;
- voditi application workflow;
- kreirati/commitovati DB transakciju.

Primjer:

```text
WeekView
    emit appointment_clicked(id)
```

a NE:

```text
WeekView
    store.mark_arrived(id)
```

## 3.2 Controller

Controller smije:
- slušati View signale;
- otvarati odgovarajući dialog;
- pretvarati UI input u service poziv;
- koordinirati više service operacija;
- osvježiti View nakon uspjeha;
- mapirati očekivanu service grešku u user-facing feedback.

Controller NE smije:
- raditi SQL query;
- sadržavati overlap pravilo;
- sadržavati working-hours pravilo;
- formatirati veliki QSS;
- crtati widgete.

## 3.3 Services

Services su jedini vlasnici poslovne logike.

Service sloj:
- appointment CRUD;
- status tranzicije;
- availability;
- TimeOff;
- working-hours pravila;
- request processing;
- settings mutacije;
- DTO/read modele;
- transakcije.

Service NE zna:
- PySide6;
- QWidget;
- QDialog;
- QMenu;
- status badge boju;
- koji je trenutno otvoren tab.

---

# 4. Proces agenata za CIJELI refaktor

Za svaki task važi:

```text
Pi ili Crush
    ↓
implementacija u zasebnom worktree-u
    ↓
pytest + ruff + mypy
    ↓
Codex nezavisan review
    ↓
Claude nezavisan review
    ↓
Radovan human approval
    ↓
merge u main
    ↓
post-merge full gate
```

Za ovaj architecture-cleanup paket se namjerno koristi **dva reviewera** i za MEDIUM taskove — ovo je namjerno skuplje od standardnog projektnog MEDIUM procesa (koji traži samo jednog reviewera), jer paket dira hotspot fajlove koje skoro svaki GUI/servisni task dodiruje. Radovan treba potvrditi da je ovaj dodatni trošak prihvaćen za CIJELI paket (REF-00 do REF-08), ne odlučivati task-po-task.

**Napomena (Claude, 24.8.2026):** prije `git worktree add` za svaki REF-XX task, implementer mora provjeriti `python scripts/coordination.py status` i uraditi `claim --task REF-XX --agent <ime> --paths ...` — isti obrazac korišten za sve dosadašnje taskove u ovoj sesiji (DENT-022, DENT-023, DENT-IMPROVE-007, DENT-IMPROVE-009). Plan ovo ne pominje eksplicitno po task-u, ali ostaje obavezno po `AGENTS.md`.

Review nije čitanje izvještaja. Codex i Claude moraju:
- čitati diff;
- provjeriti Task Contract;
- po potrebi pokrenuti ciljane testove;
- adversarno provjeriti ključni invariant;
- odbiti task ako je samo “premješten kod” ali granice nisu popravljene;
- odbiti task ako implementer proširi scope.

---

# 5. Globalni forbidden scope

Tokom REF-01 do REF-08 NE dirati:

```text
migrations/**
src/dentaland/models.py
backend/public auth/RBAC
PostgreSQL migraciju
EXCLUDE constraint
token/cancel public flow
privacy schema
audit schema
web booking UX
multi-tenancy
```

Sve što traži novu migraciju ili DB constraint izlazi iz ovog paketa i postaje zaseban HIGH task.

---

# 6. Globalni Definition of Done

Cijeli paket nije gotov dok:
- `main_window.py` više nije appointment/scheduler god-object;
- `booking.py` više nije settings + availability + appointment + request facade monolit;
- overlap/availability nema dupliranu poslovnu logiku;
- DayView/WeekView ne koriste jedan drugi kao shared utility modul;
- View sloj nema poslovnu logiku;
- Controller sloj postoji i stvarno koordinira UI workflow;
- Services ostaju jedini vlasnici poslovnih pravila;
- scheduler koristi range-based read contract;
- jedan refresh view-a ne radi nepotrebne ponovljene DB fetch-eve;
- svih 298+ postojećih testova i svi novi testovi prolaze;
- Ruff i mypy su čisti;
- nema promjene korisničkog ponašanja osim eksplicitno odobrenih korekcija.

---

# 7. REF-00 — Arhitektonska sigurnosna mreža prije refaktora

**Implementer:** Pi  
**Risk:** LOW/MEDIUM  
**Cilj:** zaključati trenutno ponašanje prije premještanja koda.

**Napomena (Claude, 24.8.2026):** risk tier ostaje LOW/MEDIUM (task samo dodaje testove, ne dira produkcijski kod — ispravno klasifikovano), ali ovaj task je efektivno jedina sigurnosna mreža za svih sedam narednih taskova koji diraju hotspot fajlove. Ne žuriti ga zbog niskog risk tier-a — ako characterization testovi promaše nešto, cijeli lanac REF-01..08 gradi na pogrešnoj pretpostavci o "trenutnom ponašanju".

## allowed_paths

```text
tests/**
agent_reports/**
docs/**
```

## forbidden_paths

```text
desktop/**
src/dentaland/**
backend/**
migrations/**
```

## Zadaci

1. Napraviti characterization test listu za:
   - create appointment;
   - edit;
   - move;
   - cancel;
   - delete;
   - status transitions;
   - web request confirm/reject;
   - Day/Week switch;
   - doctor filter;
   - TimeOff/block rendering;
   - print action;
   - status summary.
2. Identifikovati mjesta gdje trenutni testovi testiraju implementacijski detalj umjesto contracta.
3. Dodati samo testove koji nedostaju da bi refaktor imao sigurnu granicu.
4. Za GUI testove koji zavise od layout geometrije ne vjerovati `width()/sizeHint()` bez adversarne provjere.

## Acceptance

- [ ] full baseline prolazi;
- [ ] postoji mapa ključnih ponašanja -> testovi;
- [ ] nema produkcijskog koda dirnutog;
- [ ] reviewer može jasno vidjeti koji test štiti koji workflow.

## Review fokus

**Codex:** test kvalitet, da li novi test zaista pada kad se invariant pokvari.  
**Claude:** da testovi ne zaključavaju lošu arhitekturu ili privatne implementacijske detalje.

**STOP. Merge tek poslije Radovan approval-a.**

---

# 8. REF-01 — Centralizovati availability invariant

**Implementer:** Crush  
**Risk:** MEDIUM  
**Zavisnost:** REF-00

## Cilj

Ukinuti dupliranu overlap logiku i napraviti jedan servisni source of truth za provjeru dostupnosti.

## Novi odgovorni modul

```text
src/dentaland/services/availability.py
```

## Prva iteracija — behavior preserving

Prvo izdvojiti samo postojeću overlap semantiku:

```python
validate_appointment_overlap(
    session,
    doctor_id,
    start,
    end,
    exclude_id=None,
)
```

Pozivaoci:

```text
Appointment create
Appointment update
Appointment move
Public request confirm
```

`requests.py` više ne smije imati svoju kopiju overlap SQL-a.

## Nalaz review-a (Claude, 24.8.2026) — DVIJE odvojene `OverlapError` klase, ne jedna

Provjereno u kodu: `booking.py:135` i `requests.py:30` definišu **dvije nezavisne** klase istog imena `OverlapError` — nisu ista klasa, samo isto ime. Svaka ima tačno jednog poznatog potrošača:

```text
booking.OverlapError    ← desktop (main_window.py / dialog kod, preko dentaland.services re-eksporta)
requests.OverlapError   ← backend/main.py:172 (except OverlapError)
```

Formulacija "postojeći exception contract ostaje kompatibilan" u Acceptance-u nije dovoljno precizna dok se ne odluči **koja klasa preživljava** objedinjavanje. Implementer MORA:

1. eksplicitno odabrati jednu kanoničnu `OverlapError` klasu (preporuka: definisati je u `availability.py`, oba modula je re-eksportuju za backward-compat import putanje);
2. ažurirati OBA catch mjesta (`backend/main.py:172` i desktop dialog kod) u ISTOM commitu, ne odvojeno;
3. dodati test koji dokazuje da i `backend` API poziv i desktop poziv i dalje hvataju ispravnu grešku poslije izmjene (ne samo da "postojeći testovi prolaze" — postojeći testovi možda ne razlikuju dvije klase istog imena ako se import putanja promijeni tiho).

## Druga iteracija unutar istog taska samo ako review potvrdi da nema skrivenog ponašanja

U AvailabilityService objediniti read pomoćnike koji prirodno pripadaju dostupnosti:
- TimeOff read;
- working-hours intervals;
- calendar blocks;
- split-shift breaks.

Ali NE uvoditi nova poslovna pravila u ovom tasku.

## allowed_paths

```text
src/dentaland/services/availability.py
src/dentaland/services/booking.py
src/dentaland/services/requests.py
src/dentaland/services/__init__.py
tests/test_services.py
tests/test_requests.py
tests/test_availability.py
agent_reports/**
```

## forbidden_paths

```text
desktop/**
models.py
migrations/**
backend/main.py
```

## Acceptance

- [ ] samo jedna implementacija overlap query-ja;
- [ ] create/update/move/confirm request koriste istu provjeru;
- [ ] `exclude_id` ponašanje ostaje;
- [ ] **jedna kanonična `OverlapError` klasa** (ne dvije istoimene), oba pozivna mjesta (`backend/main.py`, desktop dialog kod) ažurirana i eksplicitno testirana da hvataju ISTU klasu — vidi "Nalaz review-a" iznad;
- [ ] nema UI izmjene;
- [ ] nema nove migracije.

**STOP.**

---

# 9. REF-02 — Range-based scheduling reads + eager loading

**Implementer:** Pi  
**Risk:** MEDIUM  
**Zavisnost:** REF-01

## Cilj

Uvesti servisni read contract:

```python
appointments_for_range(
    range_start,
    range_end,
    doctor_id=None,
)
```

SQL semantika:

```text
Appointment.start_time < range_end
AND
Appointment.end_time > range_start
```

Doctor i Service podatke učitati bez N+1 obrasca (`selectinload` ili `joinedload`, prema evidence-u).

## Backward compatibility

`all_combined()` ne uklanjati odmah ako ga drugi kod još koristi.

Prvo:
- dodati range API;
- prebaciti Day/Week;
- izmjeriti reference;
- tek kasniji task može ukloniti stari API.

## Performance evidence

Implementer mora napraviti mjerljiv dokaz:
- baza sa više hiljada istorijskih termina;
- Day query vraća samo relevantni period;
- Week query vraća samo relevantni period;
- doctor/service ne rade N+1.

**Napomena (Claude, 24.8.2026):** dokaz mora uključivati mjerenje **PRIJE** izmjene (broj vraćenih redova/upita na starom `all_combined()` pristupu na istoj testnoj bazi), ne samo poslije. Bez "prije" brojke, tvrdnja o poboljšanju je neprovjerljiva — isti princip kao i ranije u ovoj sesiji kod DENT-022 runde 1, gdje je neprovjerena tvrdnja u izvještaju prošla neopaženo dok je nije uhvatio nezavisan review. Ne ponavljati tu grešku ovdje unaprijed.

## Acceptance

- [ ] DayView ne koristi cijelu istoriju;
- [ ] WeekView ne koristi cijelu istoriju;
- [ ] range overlap semantika testirana na terminima koji prelaze granicu dana/sedmice;
- [ ] eager-loading ponašanje dokazano;
- [ ] nema GUI behavior promjene.

**STOP.**

---

# 10. REF-03 — Razbiti `booking.py` po servisnim odgovornostima

**Implementer:** Crush  
**Risk:** MEDIUM  
**Zavisnosti:** REF-01 + REF-02

## Cilj

`booking.py` više ne smije biti centralni servis za sve što aplikacija radi.

## Ciljna podjela

### `appointments.py`

Vlasnik:
- Appointment DTO;
- get;
- range reads;
- create;
- update;
- move;
- cancel;
- delete;
- status transitions;
- service options potrebne appointment editoru.

### `availability.py`

Vlasnik:
- overlap invariant;
- TimeOff read/write;
- working-hours availability read;
- calendar blocks;
- breaks.

### `settings.py`

Vlasnik:
- doctor activation/settings;
- services CRUD/settings;
- working-hours administration.

### `requests.py`

Ostaje vlasnik pending request lifecycle-a, ali koristi `availability.py` za scheduling invariant.

## Kompatibilnost sa GUI-jem

Ne prebacivati cijeli GUI na nove servise u istom tasku.

Dozvoljena strategija je privremeni facade `AppointmentService`, ali facade mora biti jasno označen kao compatibility seam i više nije mjesto za nove funkcije.

## Acceptance

- [ ] appointment CRUD/status više fizički nije pomiješan sa settings logikom;
- [ ] request overlap ne duplira SQL;
- [ ] compatibility API ostaje dovoljno stabilan da GUI i dalje radi;
- [ ] `PROJECT_MAP.md` opisuje stvarno stanje;
- [ ] full test suite prolazi.

**STOP.**

---

# 11. REF-04 — Uvesti pravi Controller sloj za appointment workflow

**Implementer:** Pi  
**Risk:** MEDIUM  
**Zavisnost:** REF-03

## Cilj

Izvući workflow iz `MainWindow`.

## Novi modul

```text
desktop/controllers/appointment_controller.py
```

## Controller preuzima

- new appointment;
- edit;
- details;
- move;
- cancel;
- delete;
- status action;
- user-facing service error mapping;
- refresh callback nakon mutacije.

## MainWindow poslije taska

Treba uglavnom raditi:
- construct views;
- construct controller;
- wire high-level page navigation;
- show main shell.

## Dependency injection

Controller prima service/facade kroz konstruktor. Ne uvoditi repository framework.

## Acceptance

- [ ] MainWindow nema direktnu implementaciju appointment CRUD workflow-a;
- [ ] status akcije više nisu implementirane u MainWindow;
- [ ] Controller ne importuje SQLAlchemy;
- [ ] View ne preuzima service logiku;
- [ ] svi postojeći dialogs i UX ostaju isti.

**STOP.**

---

# 12. REF-05 — Scheduler Controller + refresh orchestration

**Implementer:** Crush  
**Risk:** MEDIUM  
**Zavisnosti:** REF-02 + REF-04

## Cilj

MainWindow ne treba koordinirati:
- Day/Week state;
- current date/week;
- doctor filter;
- schedule refresh;
- status summary;
- doctor counts.

## Novi modul

```text
desktop/controllers/schedule_controller.py
```

## Ključna promjena

Jedan refresh aktivnog scheduler view-a treba učitati jedan snapshot podataka za taj period.

```text
ScheduleController.refresh()
    ↓
service.appointments_for_range(...)
service.calendar_blocks_for_range(...)
    ↓
ScheduleSnapshot / isti dataset
    ↓
active view.render(...)
status summary iz ISTOG dataseta
doctor counts iz ISTOG dataseta
```

Ne mora se uvoditi formalni dataclass ako nije potreban, ali jedan refresh ne smije ponovo i ponovo fetchovati iste appointmentse.

## Auto-refresh

20s polling može ostati, ali refreshuje samo relevantni aktivni view/page.

## Acceptance

- [ ] Day/Week state nije u MainWindow workflow logici;
- [ ] jedan scheduler refresh nema višestruke appointment fetch-eve za counts/render;
- [ ] skriveni view se ne refreshuje bez potrebe;
- [ ] status summary ostaje tačan;
- [ ] doctor counts ostaju tačni;
- [ ] 20s timer ne pokreće redundantne DB queryje.

## Evidence

Dodati fake-store/query-counter test koji deterministički dokazuje broj fetch poziva tokom jednog refresh-a.

**STOP.**

---

# 13. REF-06 — Izdvojiti shared presentation logiku iz WeekView/DayView

**Implementer:** Pi  
**Risk:** LOW/MEDIUM  
**Zavisnost:** REF-05

## Cilj

DayView više ne smije koristiti WeekView kao utility modul.

## Izdvojiti samo ono što je stabilno i zajedničko

Preporučeni kandidati:

```text
desktop/presentation/schedule_status.py
desktop/presentation/schedule_palette.py
desktop/presentation/slot_math.py
desktop/presentation/appointment_menu.py
```

NE praviti `BaseSchedulerView` samo zato što postoje dva view-a.

Inheritance uvoditi samo ako reviewer potvrdi stvarnu stabilnu zajedničku apstrakciju.

**Nalaz review-a (Claude, 24.8.2026):** stvarni uvoz je gori nego "dijeljena presentation logika" — `day_view.py` uvozi `from desktop.views.week_view import STATUS_META, WeekView, _status_key, status_icon`, uključujući `_status_key`, **privatan simbol** (vodeći underscore) preko granice modula, i sam `WeekView` (konkretnu klasu, ne samo utility). Implementer treba posebno provjeriti zašto je `WeekView` uvezen u `day_view.py` (da li se stvarno koristi, ili je leftover import) prije nego odluči gdje taj kod pripada.

## Acceptance

- [ ] `day_view.py` ne importuje shared util-e iz `week_view.py`;
- [ ] status/palette pravila su jedna istina;
- [ ] DayView i WeekView ostaju odvojeni konkretni widgeti;
- [ ] nema mega-base klase.

**STOP.**

---

# 14. REF-07 — Request i Print controller granice

**Implementer:** Crush  
**Risk:** LOW/MEDIUM  
**Zavisnost:** REF-04

## Cilj

Dovršiti Controller sloj tamo gdje MainWindow još koordinira application workflow.

## RequestController

Preuzima application-level workflow koji dijele:
- RequestsPage;
- Dashboard panel;
- ProcessRequestDialog.

Poslovna logika ostaje u `services/requests.py`.

Ako postojeći `process_pending_request(...)` helper već dobro radi kao application coordinator, ne duplicirati ga — premjestiti/inkapsulirati ga u Controller.

## PrintController

Preuzima:
- izbor print scope-a;
- poziv print service-a;
- kreiranje/otvaranje print document workflow-a.

`print_schedule.py` ostaje Service.

## Acceptance

- [ ] MainWindow ne koordinira request processing;
- [ ] MainWindow ne nosi detaljan print workflow;
- [ ] request business rules ostaju u service sloju;
- [ ] print data priprema ostaje u service sloju.

**STOP.**

---

# 15. REF-08 — Theme/QSS, timezone dependency i završni cleanup

**Implementer:** Pi  
**Risk:** LOW  
**Zavisnosti:** REF-04..07

## Theme

Veliki globalni QSS izvući iz `main_window.py` u:

```text
desktop/presentation/theme.py
```

ili `.qss` resource ako packaging ostane jednostavan.

Pošto postoji PyInstaller packaging, reviewer mora provjeriti packaged build.

## Timezone

Production kod ne treba importovati:

```python
from desktop.fake_data import SARAJEVO
```

Premjestiti zajedničku timezone konstantu u stabilan modul, npr.:

```text
src/dentaland/timezone.py
```

`fake_data.py` zatim importuje iz tog modula, ne obrnuto.

**Nalaz review-a (Claude, 24.8.2026):** `from desktop.fake_data import SARAJEVO` se pojavljuje na PET mjesta, ne samo u `main_window.py` — provjereno gre-om u kodu: `blockout_panel.py`, `day_view.py`, `week_view.py`, `dialogs/blockout_delete_confirm.py`, `main_window.py`. Allowed_paths za ovaj task treba eksplicitno uključiti sva pet, ne samo `main_window.py` + novi modul.

## MainWindow cilj poslije REF-08

Treba sadržavati uglavnom:
- window construction;
- sidebar/page registration;
- high-level routing;
- controller construction/wiring;
- window-level lifecycle.

## Acceptance

- [ ] globalni theme više nije ugrađen u MainWindow workflow kod;
- [ ] production view ne zavisi od fake_data;
- [ ] PyInstaller build i dalje radi;
- [ ] Project Map opisuje novu arhitekturu.

**STOP.**

---

# 16. Šta NAMJERNO nije dio ovog plana

## DB indeksi

Mogu biti korisni prije većeg volumena, ali zahtijevaju migraciju. Nakon REF-02 prikupiti `EXPLAIN QUERY PLAN`; ako indeks ima dokazanu korist, napraviti zaseban HIGH schema task.

## PostgreSQL / EXCLUDE

Ne dirati sada.

Refaktor treba pripremiti čist application/service contract da kasniji prelazak na:

```text
Desktop -> HTTP -> FastAPI -> PostgreSQL
```

ne zahtijeva ponovni rewrite GUI-ja.

Ali ne graditi unaprijed generički `Repository<T>` ili kompleksan gateway framework.

## Full availability behavior correction

REF-01 centralizuje postojeća pravila.

Poseban naredni task treba odlučiti da li create/edit/move/confirm moraju service-side blokirati:
- TimeOff;
- van radnog vremena;
- split-shift;
- buffer.

To je ponašajna promjena i ne treba je tiho sakriti u refaktor.

---

# 17. Preporučeni raspored Pi / Crush

```text
REF-00 Pi
   ↓
REF-01 Crush
   ↓
REF-02 Pi
   ↓
REF-03 Crush
   ↓
REF-04 Pi
   ↓
REF-05 Crush
   ↓
REF-06 Pi
   ↓
REF-07 Crush
   ↓
REF-08 Pi
```

Namjerno je skoro sekvencijalno jer svi najvažniji taskovi diraju hotspot fajlove. Forsirani paralelizam bi povećao merge konflikte.

---

# 18. Obavezni Reviewer Context Pack za svaki task

Implementer daje Codexu i Claudeu:

1. Task Contract.
2. Base commit SHA.
3. Head commit SHA.
4. `git diff --stat`.
5. puni diff.
6. listu dirnutih fajlova.
7. test komande i output.
8. ruff output.
9. mypy output.
10. impact analysis — ko poziva premještene simbole.
11. `OUT_OF_SCOPE_FINDING` listu.
12. rollback plan.

Reviewer ne smije prihvatiti tvrdnju “testovi prolaze, dakle refaktor je dobar” bez provjere layer granica.

---

# 19. Poseban review checklist — View / Controller / Services

## View

- Da li View direktno poziva business mutation?
- Da li View zna za Session/SQLAlchemy?
- Da li View odlučuje scheduling pravilo?
- Da li View koordinira više servisa?

Ako DA → blocking finding.

## Controller

- Da li Controller ima SQL query?
- Da li Controller sadrži overlap/working-hours pravilo?
- Da li Controller formatira theme/QSS?
- Da li Controller pravi domain model?

Ako DA → blocking finding.

## Services

- Da li servis uvozi PySide6?
- Da li servis zna koji tab je aktivan?
- Da li postoji ista business odluka na dva mjesta?
- Da li novi service ponovo postaje catch-all god-object?

Ako DA → blocking finding.

---

# 20. Finalni arhitektonski acceptance review poslije REF-08

Codex i Claude rade poseban audit bez implementacije.

Moraju mapirati najmanje ove tokove:

```text
USER ACTION
    ↓
VIEW SIGNAL
    ↓
CONTROLLER
    ↓
SERVICE
    ↓
DATABASE
    ↓
DTO/RESULT
    ↓
CONTROLLER
    ↓
VIEW REFRESH
```

Provjeriti:
1. Create appointment.
2. Edit appointment.
3. Move appointment.
4. Cancel appointment.
5. Status change.
6. Delete.
7. Web request processing.
8. Day refresh.
9. Week refresh.
10. Print.
11. TimeOff/blockout.
12. Settings izmjenu.

Ako jedan application workflow ide `View -> Service -> View` bez Controllera, plan nije završen.

Ako ide `Controller -> SQLAlchemy`, plan nije završen.

Ako postoje dvije implementacije iste business odluke, plan nije završen.

---

# 21. Mjerljivi kriterijumi uspjeha

## Arhitektura

- 0 SQLAlchemy importa u `desktop/views/`.
- 0 PySide6 importa u `src/dentaland/services/`.
- 1 source of truth za overlap invariant.
- `MainWindow` više ne implementira appointment CRUD/status workflow.
- Settings logika nije u appointment service-u.
- DayView ne koristi WeekView kao shared utility modul.

## Performance

- Day/Week koriste range query.
- appointment read ne radi N+1 doctor/service pattern.
- jedan scheduler refresh koristi jedan appointment dataset/snapshot.

## Proces

- svaki task: Pi/Crush implementation;
- Codex review;
- Claude review;
- Radovan approval;
- post-merge gate.

## Kvalitet

- full pytest baseline ne opada;
- Ruff clean;
- mypy clean;
- nema neodobrene schema promjene;
- nema UX regressiona.

---

# 22. Kill / rollback pravila

Refaktor task se vraća ili zaustavlja ako:

1. broj dirnutih modula neočekivano poraste > ~2x iz Task Contracta;
2. implementer mora dirati migraciju/model da bi “samo refaktorisao”;
3. GUI behavior mora biti promijenjen da bi nova struktura radila;
4. controller extraction uvodi kružne importe;
5. novi facade/postojeći facade postane još veći;
6. testovi moraju biti masovno prepisani samo zato što su vezani za privatnu implementaciju;
7. performance task nema mjerljiv dokaz da query shape postaje bolji.

Tada:
- STOP;
- zabilježiti finding;
- vratiti task na replanning;
- ne progurati izmjenu samo zato što je puno rada već urađeno.

---

# 23. Šta poslije ovog refaktora

Tek nakon finalnog architecture review-a ima smisla nastaviti Prioritet C / Fazu 1.

Tada cilj postaje:

```text
PySide6 View
    ↓
Controller
    ↓
HTTP/API client service
    ↓
FastAPI
    ↓
PostgreSQL
```

Zahvaljujući ovom cleanup-u, GUI ne bi trebalo ponovo prepisivati — mijenja se servisni adapter/transport, dok View i veliki dio Controller sloja ostaju stabilni.

---

# 24. Konačno načelo

Svaka buduća funkcija mora odgovoriti na pitanje prije koda:

```text
Da li je ovo:
VIEW?
CONTROLLER?
SERVICE?
```

Ako odgovor glasi:

```text
"najlakše je dodati još jednu metodu u MainWindow"
```

ili:

```text
"najlakše je dodati još jednu funkciju u AppointmentService"
```

to više nije dovoljan razlog.

Cilj ovog refaktora nije estetski uredniji repo. Cilj je vratiti arhitekturu u stanje gdje:

```text
View prikazuje.
Controller koordinira.
Service odlučuje.
Database čuva i garantuje ono što pripada bazi.
```
