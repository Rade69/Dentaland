---
task_id: DENT-DESKTOP-B2
risk: MEDIUM
implementer: pi
reviewer: claude
status: REVIEWED PASS — čeka human approval; vidi agent_reports/2026-08-19-DENT-DESKTOP-B2-vizuelni-polish.md
created_at: 2026-08-19
---

# Task Contract — DENT-DESKTOP-B2: Vizuelni polish dijaloga (prije Faze D)

Porijeklo: nakon Faze C, Radovan je uporedio live aplikaciju sa originalnim
mockup slikama (date na početku ovog redizajna, dokumentovane u
`docs/dentaland-desktop-agent-implementation-spec.md` istoriji) i primijetio
da su dijalozi funkcionalno gotovi ali vizuelno ne odgovaraju mockapima.
Claude je nezavisno potvrdio uživo (screenshot poređenje) i identifikovao
konkretne razlike ispod. Odlučeno je da se ovo popravi PRIJE Faze D, jer
`BaseDialog` je zajednička osnova koju D nasljeđuje — bolje popraviti
temelj sad nego duplirati posao poslije.

```yaml
id: DENT-DESKTOP-B2
title: "Vizuelni polish dijaloga (Detalji/Editor/Pomjeri/Otkaži) prema mockapima"
risk: MEDIUM
objective: >
  Uskladiti izgled postojećih dijaloga (Faza B: AppointmentEditorDialog;
  Faza C: AppointmentDetailsDialog, MoveAppointmentDialog,
  CancelAppointmentDialog) sa originalnim mockapima. Ovo je ČISTO
  vizuelni/layout zadatak — nijedna poslovna logika, store poziv, signal
  ili povratna vrijednost (get_data/selected_action/validate) se ne
  smije mijenjati. MainWindow i WeekView se NE diraju.

  Konkretne razlike identifikovane poređenjem live screenshotova sa
  mockapima (vidi agent_reports/ evidence za ovaj zadatak nakon
  implementacije za prije/poslije screenshotove):

  1. AppointmentDetailsDialog trenutno je JEDNA kolona (sve odozgo nadole).
     Mokap ima DVIJE kolone: lijevo podaci pacijenta (ime/telefon/email/
     datum/vrijeme/trajanje/doktor/usluga/napomena), desno "Status termina"
     sekcija — istaknut red sa trenutnim statusom (zelena pozadina/border
     kad je npr. "Potvrđen") iznad liste dostupnih akcija.
  2. Redovi podataka u Detaljima nemaju ikonice. Mokap ima malu ikonicu u
     krugu uz svaki red (kalendar za datum, sat za vrijeme, osoba za
     pacijenta/doktora). Koristiti postojeći `svg_icon(name, color, size)`
     helper iz `desktop/views/sidebar.py` (`_ICON_PATHS` već ima "calendar",
     "clock", "user"). Za redove bez postojeće ikonice (telefon, email,
     usluga, napomena) DODATI nove unose u `_ICON_PATHS` u sidebar.py —
     isključivo dodavanje novih ključeva, ne mijenjati postojeće ikonice
     niti ostatak sidebar.py ponašanja.
  3. Akciona dugmad u Detaljima su sva identično bijela. Mokap razlikuje:
     teal outline za "Uredi termin"/"Pomjeri termin", crveni outline za
     "Otkaži termin". ("Izbriši termin" NE dodavati — Faza F, HIGH, još
     ne postoji u ovoj fazi.)
  4. AppointmentEditorDialog koristi jednostavan jednokolonski QFormLayout
     (svako polje puna širina). Mokap ima kompaktan grid: Pacijent+Doktor
     jedan pored drugog (jedan red, dvije kolone), Datum+Vrijeme+Trajanje
     u tri kolone jednog reda, Usluga puna širina, Napomena puna širina.
     Telefon+Email mogu ostati puna širina ili se upariti — po nahođenju,
     bitno je da glavni red (Pacijent/Doktor) i red datum/vrijeme/trajanje
     budu u koloni kako mokap prikazuje, ne svaki u svom redu.
  5. MoveAppointmentDialog i CancelAppointmentDialog su već blizu mokapa —
     dodati samo: (Move) malu ikonicu uz naslov/trenutno-vrijeme red; (Cancel)
     upozoravajuću ikonicu na vrhu (krug sa uskličnikom, slično postojećem
     `dialogError` stilu iz BaseDialog ali neutralne boje, ne crvene — to je
     upozorenje, ne greška) i blagu pozadinsku boju iza rečenice "Otkazani
     termin ostaje sačuvan u istoriji" (postojeći `#dialogError` stil je
     crven/za greške — napraviti novu klasu, ne reuse-ovati error stil za
     ne-error poruku).

  Ako neka od gornjih izmjena zahtijeva proširenje `BaseDialog` (npr. helper
  za red sa ikonicom, helper za dvokolonski layout, varijanta obojenog
  dugmeta) — dodati ga tamo kao reusable metodu, ne kopirati stil inline u
  svaki dijalog posebno.
allowed_paths:
  - desktop/views/dialogs/base_dialog.py
  - desktop/views/dialogs/appointment_details.py
  - desktop/views/dialogs/appointment_editor.py
  - desktop/views/dialogs/move_appointment.py
  - desktop/views/dialogs/cancel_appointment.py
  - desktop/views/sidebar.py  # ISKLJUČIVO dodavanje novih _ICON_PATHS unosa
  - tests/test_gui/test_appointment_details_dialog.py
  - tests/test_gui/test_appointment_dialog.py
  - tests/test_gui/test_destructive_dialogs.py
  - agent_reports/**
forbidden_paths:
  - src/dentaland/**
  - desktop/views/main_window.py
  - desktop/views/week_view.py
  - desktop/views/requests_panel.py
  - migrations/**
  - backend/**
  - web/**
  - CLAUDE.md
  - docs/**
acceptance:
  - AppointmentDetailsDialog ima dvokolonski layout (info lijevo, status+akcije desno), ne jednu kolonu.
  - Redovi u Detaljima imaju ikonicu (svg_icon), ne samo tekst labelu.
  - Status red je vizuelno istaknut (highlight boja/border prema trenutnom statusu), ne plain centriran badge.
  - Akciona dugmad u Detaljima su obojena po tipu (teal za edit/move, crveno-obrisano za cancel) — ne sva identična.
  - AppointmentEditorDialog koristi kompaktan grid (Pacijent+Doktor u istom redu, Datum+Vrijeme+Trajanje u istom redu), ne jednokolonski form gdje je svako polje u svom redu.
  - MoveAppointmentDialog i CancelAppointmentDialog dobijaju male vizuelne dopune opisane gore (ikonica, highlight box) bez promjene ponašanja.
  - get_data()/selected_action()/validate() potpisi i povratne vrijednosti ostaju identični (MainWindow orkestracija se ne dira i ne smije se pokvariti).
  - Nula izmjena u desktop/views/main_window.py, desktop/views/week_view.py, desktop/views/requests_panel.py, src/dentaland/**.
  - Postojeći testovi i dalje prolaze (uz eventualne dopune ako se struktura widgeta promijeni — npr. novi objectName-ovi za grid sekcije).
verification:
  - pytest tests/ -q
  - ruff check desktop tests
  - mypy src/dentaland desktop backend   # mora ostati na 6 grešaka (trenutni baseline), ne 7 niti manje/više na neočekivan način — provjeriti protiv čistog main-a prije tvrdnje
review:
  reviewers: 1
  required: [architecture, scope, visual-fidelity]
```

## Napomena implementeru (Pi)

- Nemaš direktan pristup mockup slikama (one su bile u chat poruci, ne
  fajl u repou) — oslanjaj se na tekstualni opis iznad, koji je Claude
  napisao direktno iz poređenja screenshotova. Ako nešto nije jasno iz
  opisa, stani i pitaj umjesto da nagađaš.
- Ovo NIJE prilika da se "usput" doda nešto funkcionalno (npr. Izbriši
  dugme, novi status akcije) — čisto vizuelni/layout zadatak. Sve
  funkcionalno je već prošlo review u Fazi B/C.
- Prije/poslije screenshot (čak i offscreen render sa blokovima umjesto
  teksta — layout se i dalje vidi) u evidence fajlu će ubrzati review.
