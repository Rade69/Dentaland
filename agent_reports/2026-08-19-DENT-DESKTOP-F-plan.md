# Plan prije izmjene — DENT-DESKTOP-F (hard delete termina)

Risk: HIGH. Implementer: Claude (direktno, po `CLAUDE.md`). Reviewer 1/2: Crush i Pi (nezavisno od ove sesije). Human approval: Radovan, prije merge-a.

## Cilj

Omogućiti trajno brisanje termina, isključivo za slučaj greškom kreiranog
zapisa. Odvojeno od `cancel()` (Faza C) — otkazan termin ostaje u istoriji,
izbrisan termin nestaje potpuno i nepovratno.

## Pogođeno

- `src/dentaland/services/booking.py` — nova metoda `delete(appt_id) -> None`.
- `desktop/views/dialogs/delete_appointment.py` — nov fajl, destruktivni
  confirm modal.
- `desktop/views/dialogs/appointment_details.py` — dugme "Izbriši termin",
  vizuelno odvojeno (razmak + drugačija sekcija) ispod "Otkaži termin".
- `desktop/views/dialogs/__init__.py` — export novog dijaloga.
- `desktop/views/week_view.py` i `desktop/views/day_view.py` — dodati
  "Izbriši termin" u context meni, vizuelno odvojeno (poseban separator)
  na dnu. Plan (F.2) je pisan prije Faze E (day_view.py tada nije
  postojao) — dodajem day_view.py u obim radi konzistentnosti sa week_view
  (isti akcioni set svuda drugdje već postoji u oba fajla od Faze E).
- `desktop/views/main_window.py` — `_handle_appointment_action` dobija
  granu za `"delete"`, novi `_delete_appointment(appt)` metod (isti
  orkestracioni obrazac kao `_cancel_appointment`).
- `tests/test_services.py` — testovi za `delete()`.
- `tests/test_gui/test_destructive_dialogs.py` — testovi za novi modal.
- `tests/test_gui/test_main_window.py`, `test_week_view.py`, `test_day_view.py` —
  wiring testovi.

## Fact found — FK/cascade provjera (F.3, prije koda)

Pregledao sam `src/dentaland/models.py` u cijelosti: `Appointment` ima
FK-ove KOJI IZLAZE (`doctor_id -> doctors.id`, `service_id -> services.id`)
— Appointment je dijete, Doctor/Service su roditelji. Pretraga
`grep -n "appointments.id"` u `models.py` ne vraća ništa — **nijedna druga
tabela trenutno ne referencira `appointments.id`** kao strani ključ.
`material_usage` (budući M1 modul) ne postoji u šemi. Zaključak: brisanje
reda iz `appointments` ne može izazvati cascade gubitak nikakvih drugih
podataka u trenutnoj šemi — sigurno je implementirati prost `DELETE` bez
dodatne cascade logike ili provjere.

Ovo NIJE pretpostavka nego provjerena činjenica prije pisanja koda, po
F.3 zahtjevu ("Prije implementacije provjeriti FK veze... testirati na
realnoj test bazi" — testiraću i u pytest-u, ne samo statičkom pregledu).

## Plan (redoslijed rada)

1. `booking.py`: `delete(appt_id) -> None` — dohvati po ID-u, ako ne
   postoji `raise ValueError`, inače `session.delete(appt); session.commit()`.
   Nema status-provjere kao kod `cancel()`/`mark_*` (brisanje mora raditi
   za BILO KOJI status — greška u unosu se može desiti bez obzira na
   status termina u tom trenutku; plan F.5 traži "pogrešan ID ima
   kontrolisano ponašanje", ne traži restrikciju po statusu).
2. Testovi u `test_services.py`: delete uklanja tačno jedan red (provjeriti
   `session.get()` vraća `None` poslije), pogrešan ID diže `ValueError`,
   delete NE utiče na druge termine (kreirati dva, obrisati jedan,
   provjeriti da drugi ostaje netaknut — ovo je praktični dokaz odsustva
   cascade efekta, ne samo statička FK analiza).
3. `desktop/views/dialogs/delete_appointment.py`: `DeleteAppointmentDialog`
   po uzoru na `CancelAppointmentDialog`, ali:
   - `icon="alert"` (isti kao Cancel, ili razmotriti novu "trash" ikonicu
     u `sidebar.py::_ICON_PATHS` — OUT_OF_SCOPE ako zahtijeva dodatnu
     ikonicu van onoga što F ugovor eksplicitno traži; koristiću postojeći
     "alert" da ne širim scope na sidebar.py, koji je forbidden ovdje);
   - tekst tačno po F.4 mockupu (ime pacijenta, datum/vrijeme, "Ova radnja
     trajno uklanja termin", uputstvo da se za obično otkazivanje koristi
     "Otkaži termin");
   - `add_primary_button("Izbriši termin")` ali sa EKSPLICITNIM
     `setAutoDefault(False)` i `setDefault(False)` na tom dugmetu — F.4
     traži "Enter ne aktivira delete", a `add_primary_button` inače ne
     sprečava Qt-ov default autoDefault ponašanje. Ovo je jedina namjerna
     razlika od `add_primary_button`-ovog uobičajenog ponašanja u ovom
     tasku, dokumentovana ovdje unaprijed.
   - full red primary button (isti stil kao Cancel-ov `#ef334f` override).
4. `appointment_details.py`: dodati `_add_section` razmak + novo dugme
   "Izbriši termin" (`kind="danger"` ili poseban stil da bude vizuelno
   NAJudaljenije/najupadljivije destruktivno, po F.4 "vizuelno odvojeno
   na dnu") — akcija `"delete"`.
5. `week_view.py` / `day_view.py`: dodati `menu.addSeparator()` pa
   "Izbriši termin" (`"delete"`) na dnu context menija, samo za
   NE-terminalne termine (isto pravilo kao ostale operativne akcije —
   plan ne kaže eksplicitno da delete treba biti dostupan i za
   terminalne termine, a "greškom kreiran termin" se prirodno odnosi na
   bilo koji status pa ću ovo razjasniti kao Decision required ispod).
6. `main_window.py`: `_handle_appointment_action` grana za `"delete"` →
   `_delete_appointment(appt)`; taj metod otvara `DeleteAppointmentDialog`,
   na accept poziva `store.delete(appt.id)`, refresh.
7. GUI testovi: dugme postoji i vizuelno odvojeno; klik na "Izbriši
   termin" u Detaljima/context meniju otvara modal; accept poziva
   `store.delete`; reject/X ne poziva ništa; nakon delete se scheduler
   i dashboard osvježe (termin nestaje iz prikaza).
8. Verifikacija (pytest/ruff/mypy), pa Task Contract + evidence.

## Decision required (Radovan/Ljubo — ne moja odluka)

Da li "Izbriši termin" treba biti dostupan i za TERMINALNE termine
(COMPLETED/NO_SHOW/CANCELLED), ili samo za aktivne (SCHEDULED)? Plan
teksta F.4 ne razdvaja eksplicitno. Moja preporuka: dostupno za SVE
statuse (uključujući terminalne) — "greškom kreiran termin" se može
otkriti i nakon što je već označen završenim/otkazanim, i nema
poslovnog razloga da se brisanje greške ograniči na trenutni status.
Ovo NE mijenja cancel/status tranzicije (i dalje zaključane iz Faze C),
samo određuje da li se destruktivno dugme prikazuje i na read-only
(terminalnim) prikazima Detalja. Ako se ne javi drugačija odluka,
implementiram sa ovom pretpostavkom (dostupno svuda) i to jasno
zapisujem u evidence — human approval korak je prilika da se ospori
prije merge-a.

## Šta NE dirati

- `src/dentaland/models.py`, `migrations/**` — nema šematske izmjene,
  hard delete ne traži novu kolonu niti FK promjenu.
- `src/dentaland/services/requests.py` — `confirm_request`/`reject_pending`
  tok nedirano.
- `desktop/views/requests_panel.py`, `desktop/views/sidebar.py`,
  `desktop/views/dialogs/appointment_editor.py`,
  `desktop/views/dialogs/move_appointment.py`,
  `desktop/views/dialogs/cancel_appointment.py`,
  `desktop/views/dialogs/process_request.py` — postojeći dijalozi ostaju
  netaknuti, samo `appointment_details.py` dobija novo dugme.
- `backend/**`, `web/**` — van obima.

## Plan verifikacije

```bash
pytest tests/ -q
ruff check src/dentaland desktop tests
mypy src/dentaland desktop backend   # mora ostati 6 grešaka (trenutni baseline)
```

Dodatno, uživo (offscreen Qt + prava SQLite baza, isti obrazac kao
review-i prethodnih faza): kreirati dva termina, obrisati jedan kroz
pravi `store.delete()`, potvrditi da tačno jedan nestaje a drugi ostaje,
i da UI prikaz (WeekView/DayView/dashboard) više ne prikazuje obrisani
termin poslije refresh-a.

## Rollback

Ako se HIGH review (Crush + Pi) ili Radovan ne slože sa implementacijom:
- izmjene su izolovane u posebnom worktree-u/grani
  (`task/DENT-DESKTOP-F-hard-delete`), `main` ostaje netaknut do
  eksplicitnog merge-a;
- `delete()` metoda u `booking.py` je jedina servisna izmjena — laka za
  potpuno ukloniti bez uticaja na ostale metode (nema dijeljenog stanja);
- ako se ospori DA se `delete()` prikazuje za terminalne termine (vidi
  "Decision required"), to je UI-only izmjena (uslov u
  `appointment_details.py`/context menijima) — ne zahtijeva promjenu
  servisnog sloja niti migraciju.

## Odbačene opcije

- **Soft delete (status kolona umjesto pravog DELETE-a)** — odbačeno:
  plan eksplicitno traži "hard delete", i `AppointmentStatus` enum već
  ima `CANCELLED` za taj slučaj (soft-delete bi dupliralo cancel
  semantiku bez jasne razlike, i zahtijevalo bi šematsku izmjenu koju
  CLAUDE.md izričito zabranjuje za ovaj zadatak).
- **Cascade/ORM `passive_deletes`/`ondelete="CASCADE"` na FK-ovima** —
  nepotrebno, jer FK-ovi idu IZ `Appointment` KA `Doctor`/`Service`, ne
  obrnuto; nema šta da se kaskadno obriše.
- **Nova "trash" SVG ikonica u `sidebar.py`** — razmotreno za
  `DeleteAppointmentDialog` header, odbačeno radi manjeg obima
  (`sidebar.py` je forbidden path za ovaj zadatak); koristi se postojeća
  "alert" ikonica, isto kao Cancel.
