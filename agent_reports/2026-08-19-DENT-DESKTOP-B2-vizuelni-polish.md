# Implementer izveštaj — DENT-DESKTOP-B2 (vizuelni polish dijaloga)

Task: DENT-DESKTOP-B2 | Risk: MEDIUM | Implementer: pi | Status: REVIEWED PASS — čeka human approval (vidi Review niže)

## Cilj faze

Uskladiti izgled dijaloga (Detalji/Editor/Pomjeri/Otkaži) sa originalnim mockapima —
čisto vizuelni/layout zadatak. NIJEDNA poslovna logika, store poziv, signal ni
povratna vrijednost (get_data/selected_action/validate) nije mijenjana.
MainWindow/WeekView/servisni sloj netaknuti.

## Izmijenjeni fajlovi (svi u allowed_paths)

- `desktop/views/dialogs/base_dialog.py` — reusable helperi + stilovi
- `desktop/views/dialogs/appointment_details.py` — dvokolonski + ikonice + highlight + obojena dugmad
- `desktop/views/dialogs/appointment_editor.py` — kompaktan grid
- `desktop/views/dialogs/move_appointment.py` — ikonica uz "Trenutno"
- `desktop/views/dialogs/cancel_appointment.py` — warning ikonica + highlight box
- `desktop/views/sidebar.py` — samo dodati `_ICON_PATHS` unosi (phone, mail, note, alert)

## Šta je urađeno (mapirano na acceptance)

1. **Detalji — dvokolonski layout**: lijevo podaci pacijenta (QGridLayout), desno
   "Status termina" sekcija (QVBoxLayout). Nije više jedna kolona.
2. **Redovi sa ikonicom**: svaki red ima `make_icon_label(...)` — ikonica u krugu
   (kalendar/clock/user/phone/mail/tooth/note) uz labelu i vrijednost.
3. **Status red istaknut**: `statusHighlight` — obojena pozadina/border prema
   statusu (`_STATUS_BG` mapa), ne plain centriran badge.
4. **Obojena akciona dugmad**: "Uredi termin"/"Pomjeri termin" = teal outline
   (`outlineTealButton`), "Otkaži termin" = crveni outline (`outlineDangerButton`);
   statusne akcije ostaju neutralne. "Izbriši termin" NIJE dodavan (Faza F).
5. **Editor — kompaktan grid**: Pacijent+Doktor u istom redu, Datum+Vrijeme+Trajanje
   u tri kolone jednog reda, Telefon+Email upareni, Usluga i Napomena puna širina.
6. **Pomjeri** — mala ikonica (clock) uz "Trenutno" red.
7. **Otkaži** — upozoravajuća ikonica (alert, amber `#b7791f`) na vrhu + napomena
   "Otkazani termin ostaje sačuvan u istoriji." u `cancelNoteBox` (neutralni
   highlight, NE crveni error stil).

## BaseDialog helperi (reusable, ne inline kopije)

- `make_icon_label(icon_name, color, size)` — ikonica u krugu.
- `add_outline_button(text, kind="teal")` — obojeno obrisano dugme (teal/danger).
- Stilovi `#outlineTealButton`/`#outlineDangerButton`/`#editorFieldLabel` u
  zajedničkom stylesheet-u.

## Verifikacija

```
pytest tests/test_gui/test_appointment_details_dialog.py tests/test_gui/test_appointment_dialog.py tests/test_gui/test_destructive_dialogs.py -q  → 21 passed
pytest tests/ -q  → 184 passed
ruff check desktop tests  → All checks passed!
mypy src/dentaland desktop backend  → 6 errors (baseline, nula novih)
```

Postojeći testovi prolaze BEZ izmjena — struktura widgeta je sačuvana
(`status_badge`, `_action_buttons`, `name_edit`/`doctor_combo`/`duration_edit`/
`get_data()`/`selected_action()`/`validate()` identični).

## Scope potvrda

`git status` pokazuje izmjene samo u `allowed_paths` (5 dialogs fajlova + sidebar.py).
Nijedan `forbidden_path` nije diran — posebno `main_window.py`, `week_view.py`,
`requests_panel.py`, `src/dentaland/**`.

## Napomena o screenshotovima

Nema mockup slika u repou (bile u chat poruci) — radio sam po Claude-ovom
tekstualnom opisu iz Task Contracta. Layout promjene su offscreen-testabilne
(svi widgeti i dalje postoje), ali prije/poslije screenshot nije generisan.

## Review (Claude, Reviewer 1) — nezavisna provjera

```yaml
verdict: REJECT
scope: PASS
acceptance: FAIL
architecture: PASS
security: PASS
blocking_findings:
  - location: desktop/views/dialogs/cancel_appointment.py (note_box, QFrame objectName "cancelNoteBox")
    rule: "Task Contract acceptance #6 — CancelAppointmentDialog treba blagu pozadinsku boju iza napomene o istoriji, u NOVOJ stilskoj klasi (ne error stil). Live render pokazuje čisto bijelu pozadinu (255,255,255), ne #fff8e6 kako QSS definiše — QFrame ignoriše background-color/border iz stylesheet-a bez Qt.WidgetAttribute.WA_StyledBackground, koji nije postavljen."
```

### Nezavisno provjereno

- `pytest tests/ -q` → 184 passed (potvrđeno, BEZ izmjena test fajlova —
  implementer je stvarno sačuvao sve postojeće atribute/potpise).
- `ruff check desktop tests` → All checks passed.
- `mypy src/dentaland desktop backend` → 6 grešaka, tačno baseline, nula novih.
- `git diff --stat` — tačno `allowed_paths` (5 dialog fajlova + sidebar.py),
  nula dodira `forbidden_paths`. `sidebar.py` diff pregledan red-po-red —
  isključivo 4 nova `_ICON_PATHS` unosa (phone/mail/note/alert), ništa
  postojeće izmijenjeno.
- Pročitan pun diff svih 6 fajlova (ne samo izvještaj) — `get_data()`,
  `selected_action()`, `validate()`, imena atributa (`status_badge`,
  `_action_buttons`, `name_edit`, `doctor_combo`, ...) su identični Fazi
  B/C — zato test fajlovi nisu ni trebali izmjenu, tvrdnja iz izvještaja
  je tačna.

### Živa vizuelna provjera (renderovao sam sve 4 dijaloga uživo, offscreen Qt + prava baza)

- **AppointmentDetailsDialog** — potvrđeno dvokolonski layout, ikonica uz
  svaki red (person/phone/mail/calendar/clock/tooth/note — svi vidljivi u
  teal krugovima), status highlight (zelena pozadina za "Potvrđen" —
  potvrđeno da boja REALNO renderuje, ne samo u kodu), teal outline dugmad
  za Uredi/Pomjeri, crveno-obrisano dugme za Otkaži — sve vizuelno
  razdvojeno. **Odgovara acceptance kriterijumima 1-3 potpuno.**
- **AppointmentEditorDialog** — potvrđeno kompaktan grid: Pacijent+Doktor
  isti red, Datum+Vrijeme+Trajanje isti red (tri kolone), Telefon+Email
  isti red, Usluga/Napomena puna širina. **Odgovara acceptance 4 potpuno.**
- **MoveAppointmentDialog** — clock ikonica vidljiva uz "Trenutno" red.
  **Odgovara acceptance 5.**
- **CancelAppointmentDialog** — upozoravajuća ikonica (amber trougao)
  VIDLJIVA i ispravna. Ali sam uzorkovao piksele na mjestu gdje bi
  `cancelNoteBox` pozadina trebala biti (`PIL.Image.getpixel`) — rezultat
  je `(255, 255, 255)` na sve tri testirane tačke, čisto bijelo, ne
  `#fff8e6` kako QSS pravilo definiše. **Acceptance 6 (highlight box) NE
  radi u praksi**, iako je kod ispravno napisan (QFrame + QSS pravilo
  postoje) — poznat Qt gotcha: `QFrame` ne primjenjuje
  `background-color`/`border` iz stylesheet-a bez eksplicitnog
  `setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)`. Za
  poređenje: `status_badge` (QLabel) i `make_icon_label` krugovi (QLabel)
  RADE ispravno bez tog atributa — QLabel obično poštuje background-color
  bez dodatnog atributa, QFrame ne uvijek. Ovo je razlog zašto je greška
  lako promakla čitanjem koda — sintaksno je sve na svom mjestu.

### Zaključak

Sve OSTALO je odlično izvedeno i uživo potvrđeno — 5 od 6 acceptance
stavki rade tačno kako je traženo, arhitektura je čista (reusable
`make_icon_label`/`add_outline_button` u `BaseDialog`, ne kopirano po
dijalozima), scope je disciplinovan. `REJECT` (ne `PASS_WITH_NOTES`) samo
zato što je fix doslovno jedna linija koda za jasno neispunjen,
imenovan acceptance kriterijum — jeftinije popraviti i re-verifikovati
nego pustiti "izgleda ispravno u kodu, ali ne radi na ekranu" kroz.

**Traženo prije ponovnog review-a:** u `cancel_appointment.py`, poslije
`note_box = QFrame()`, dodati:
```python
note_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
```
(`Qt` je već uvezen u tom fajlu). Ponovo pokrenuti vizuelnu provjeru
(screenshot + pixel sample, ili samo vizuelna potvrda) da amber pozadina
stvarno renderuje prije nego se javi da je gotovo.

## Re-verifikacija poslije fix-a (Claude) — PASS

Implementer je dodao `setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)`
i prebacio stil sa klasnog QSS selektora na direktan `note_box.setStyleSheet(...)`
poziv (funkcionalno ekvivalentno, samo direktnije). Nezavisno ponovljena
provjera:

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

- `pytest tests/ -q` → 184 passed. `ruff check desktop tests` → All checks
  passed. `mypy src/dentaland desktop backend` → 6 grešaka, baseline, nula
  novih.
- **Live pixel sample** (moj prvi pokušaj je pogrešno uzorkovao stare
  koordinate — kutija se pomjerila naniže jer je warn-ikonica dodala red
  iznad nje; ispravljeno uzorkovanjem na stvarnoj poziciji vidljivoj na
  screenshotu): `(255, 248, 230)` = tačno `#fff8e6` (pozadina), `(240, 217,
  168)` = tačno `#f0d9a8` (border, uzorkovano blizu ivice). Highlight box
  stvarno renderuje, ne samo u kodu.

**Zaključak:** DENT-DESKTOP-B2 potpuno spremno za merge — svih 6 acceptance
stavki uživo potvrđeno, arhitektura čista, scope disciplinovan kroz obje
runde. Čeka human approval (Radovan).
