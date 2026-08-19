# Implementer izveštaj — DENT-DESKTOP-E (Faza E)

Task: DENT-DESKTOP-E | Risk: MEDIUM | Implementer: pi | Status: REVIEWED PASS — čeka human approval (vidi Review niže)

## Cilj faze

Dva jasna scheduler prikaza (Dan + Sedmica), omogućen "Dan" dugme, uklonjen
redundantni "Po doktoru/Paralelno" mod, statusni summary sačuvan za oba prikaza.

## Izmijenjeni fajlovi (svi u allowed_paths)

- `desktop/views/day_view.py` (nov)
- `desktop/views/main_window.py` (mod)
- `tests/test_gui/test_day_view.py` (nov)
- `tests/test_gui/test_main_window.py` (mod)

`week_view.py` NIJE diran (DayView samo importuje male stabilne helpere iz njega —
nije zatrebalo izdvajanje).

## Šta je implementirano

- **`DayView`** (zaseban widget, ne mega-WeekView):
  - kolone = doktori (iz `store.doctors()`), redovi = vremenski slotovi 08:00–20:00;
  - termini izabranog dana, u koloni doktora i redu vremena, sa pastelnim bojama
    doktora (`WeekView._DOCTOR_CARD_PALETTE`) i status simbolom;
  - `appointment_clicked(int)` (lijevi klik na termin), `appointment_action_requested(int, str)`
    (status-aware context menu — isti tok kao WeekView), `slot_selected(object)`
    (prazan slot);
  - `visible_status_counts()` za dan (statusni summary u Dan modu);
  - dijeli `STATUS_META`/`_status_key`/`status_icon` iz week_view.
- **`main_window.py`**:
  - `DayView` + `QStackedWidget` (`view_stack`) sa WeekView/DayView;
  - "Dan" dugme omogućeno (checkable) i prebacuje na DayView; "Sedmica" vraća nazad;
  - day_view signali povezani na ISTE orkestracione metode (`_on_slot_selected`,
    `_open_appointment_details`, `_handle_appointment_action`);
  - uklonjeni "Po doktoru"/"Paralelno" (redundantni treći mod);
  - `_refresh_dashboard`/`_move_week`/`_go_today` ažuriraju oba view-a;
  - `_update_status_legend` koristi AKTIVNI view (Dan ili Sedmica counts).

## Šta namjerno NIJE urađeno

- Drag&drop u DayView (ostaje WeekView-specific za promjenu vremena; doktor se u
  Dan prikazu mijenja kroz "Uredi termin").
- Navigacija po danu (DayView prikazuje `week_start` — prvi dan sedmice; strelice
  i dalje pomjeraju sedmicu). Nije bilo u acceptance stavkama.
- Blokovi/pauze u DayView (samo termini — plan E.3 ne traži blokove za Dan).

## Verifikacija

```
pytest tests/test_gui/test_day_view.py tests/test_gui/test_main_window.py tests/test_gui/test_week_view.py -v  → 44 passed
pytest tests/ -q  → 201 passed
ruff check desktop tests  → All checks passed!
mypy src/dentaland desktop backend  → 6 errors (baseline, nula novih)
```

## Scope potvrda

`git status` pokazuje izmjene samo u `allowed_paths` (`day_view.py`, `main_window.py`,
2 test fajla, `agent_reports/**`). Nijedan `forbidden_path` nije diran — posebno
`src/dentaland/**`, `dialogs/**`, `requests_panel.py`, `sidebar.py`, `week_view.py`.

## Review (Claude, Reviewer 1) — nezavisna provjera

```yaml
verdict: REJECT
scope: PASS
acceptance: FAIL
architecture: PASS
security: PASS
blocking_findings:
  - location: desktop/views/main_window.py — _go_today(), _move_week(), _show_day_view()
    rule: "Plan E.3 'Implementirati: izabrani datum...' i E.7 DoD 'Dan radi' — Dan prikaz trenutno može prikazati SAMO ponedjeljak trenutne sedmice, nikad bilo koji drugi dan. 'Danas' dugme u Dan modu ne vodi na stvarni današnji dan (živa provjera: 19.08.2026 (srijeda) -> Danas u Dan modu prikazuje 17.08.2026 (ponedjeljak), ne 19.08.). Strelica napred/nazad pomjera 7 dana (cijelu sedmicu), nema načina da se pređe na utorak/srijedu/... unutar Dan prikaza."
```

### Nezavisno provjereno

- `pytest tests/ -q` → 201 passed. `ruff check desktop tests` → All checks
  passed. `mypy src/dentaland desktop backend` → 6 grešaka, baseline, nula
  novih.
- `git diff -- desktop/views/week_view.py` → **prazno**, potvrđeno da Sedmica
  izvor nije ni dirnut (najsigurniji mogući dokaz da nema regresije na
  postojećem, najkorišćenijem prikazu).
- `Po doktoru`/`Paralelno` uklonjeni — potvrđeno u diff-u i testu
  `test_nema_po_doktoru_paralelno`.
- `DayView` arhitektura je čista: zaseban widget (ne mega-WeekView kako plan
  dozvoljava kao opciju), dijeli samo `STATUS_META`/`_status_key`/`status_icon`
  iz `week_view.py` (čitanje, ne pisanje), isti signal-based model
  (`appointment_clicked`/`appointment_action_requested`/`slot_selected`) kao
  WeekView iz Faze C.
- Živa provjera: klik na termin u Dan prikazu STVARNO otvara
  `AppointmentDetailsDialog` (nije mrtvi kraj) — potvrđeno pozivom
  `day_view.appointment_clicked.emit(...)` protiv prave `MainWindow` instance.

### Nezavisna procjena spornog pitanja (dan-navigacija)

Implementer je ovo transparentno prijavio u "Šta namjerno NIJE urađeno" —
dobra praksa, ne skrivanje. Ali sam pročitao plan (sekcija E.3) sam i ne
slažem se sa zaključkom da nije bilo u obimu:

> "Implementirati: **izabrani datum**; doktori kao kolone; vrijeme
> vertikalno; isti appointment card mentalni model; isti details/context
> action behavior."

"Izabrani datum" u kontekstu "Dan" prikaza (za razliku od "Sedmica" koja
prikazuje fiksni raspon) razumno znači da korisnik treba moći IZABRATI koji
dan gleda — to je suštinska razlika između "prikaza jednog dana" i
"prikaza jedne sedmice". Živo sam potvrdio da to trenutno ne postoji ni u
minimalnom obliku:

```
REPRO: day_view.day right after switch: 2026-08-17 (week_start je isto)
REPRO: 'Danas' u Dan modu -> day_view.day = 2026-08-17, stvarni danas = 2026-08-19
REPRO: da li 'Danas' u Dan modu prikazuje DANAS? False
REPRO: strelica napred u Dan modu pomjera dan sa 2026-08-17 na 2026-08-24 (delta = 7 dana)
```

`DayView.set_day(day)` **već postoji** kao javni metod (implementer ga je
sam napravio, ispravno) — ograničenje nije u widgetu nego isključivo u
tome što `main_window.py` nikad ne poziva `set_day()` sa bilo čim osim
`self.week_start` (uvijek ponedjeljak). Ovo čini Dan prikaz praktično
neupotrebljivim za stvarnu svrhu (osoblje želi vidjeti DANAS ili
konkretan dan, ne uvijek ponedjeljak) — "Dan radi" iz DoD-a (E.7) nije
ispunjeno u smislenom čitanju te stavke.

### Zaključak

Sve OSTALO je odlično — arhitektura, scope disciplina, Sedmica
netaknuta, click-through potvrđen uživo, testovi za ono što JESTE
implementirano su temeljiti. Ovo NIJE trivijalan jednolinijski fix kao
B/B2, ali NIJE ni veliki redizajn — `set_day()` već postoji, treba samo
ožičiti navigaciju da bude view-mode-svjesna.

**Traženo prije ponovnog review-a:**
1. Kad je Dan aktivan, `_go_today()` treba postaviti `day_view` na
   `date.today()` (stvarni današnji dan), ne na `week_start`.
2. Kad je Dan aktivan, strelice napred/nazad treba da pomjeraju
   `day_view` za ±1 dan (ne ±7 kao Sedmica) — potrebna je grana u
   `_move_week`/nova metoda koja provjerava koji je `view_stack.currentWidget()`.
3. `_show_day_view()` (klik na "Dan" dugme) treba postaviti dan na
   `date.today()` po defaultu prilikom prvog prebacivanja, ne
   `week_start`.
4. Range label (`_update_range_label`) razmotriti da li treba
   prikazivati JEDAN dan kad je Dan aktivan umjesto uvijek sedmičnog
   raspona — kozmetički, ne blokirajuće, ali logično uz gornje izmjene.
5. Dodati test koji pokriva dan-navigaciju (Danas/strelice) dok je Dan
   aktivan — trenutno nijedan test ne pokriva ovo jer ponašanje ne
   postoji.

Napomena implementeru: ovo je moja nezavisna procjena obima na osnovu
teksta plana, ne apsolutna istina — ako se ne slažeš da je "izabrani
datum" trebalo značiti navigaciju, to je legitimna tačka za raspravu
(javi Radovanu, on je konačna riječ po CLAUDE.md hijerarhiji kad se
reviewer i implementer objektivno ne slažu oko namjere).

## Re-verifikacija poslije fix-a (Claude) — PASS

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

- `pytest tests/ -q` → 202 passed (201 + 1 novi). `ruff check desktop tests`
  → All checks passed. `mypy src/dentaland desktop backend` → 6 grešaka,
  baseline, nula novih.
- Diff `main_window.py` odgovara traženom fix-u tačno: `self.current_day`
  uveden, `_move_week`/`_go_today` granaju po `view_stack.currentWidget()`,
  `_show_day_view` koristi `current_day`. `week_view.py` i dalje potpuno
  netaknut.

### Živa re-reprodukcija (isti scenario kao u REJECT rundi)

```
REPRO: day_view.day right after switch: 2026-08-19 (week_start je 2026-08-17)
REPRO: 'Danas' u Dan modu -> day_view.day = 2026-08-19, stvarni danas = 2026-08-19
REPRO: da li 'Danas' u Dan modu prikazuje DANAS? True
REPRO: strelica napred u Dan modu pomjera dan sa 2026-08-19 na 2026-08-20 (delta = 1 dan)
REPRO: klik na termin u Dan prikazu i dalje otvara AppointmentDetailsDialog: True
```

Svi identifikovani problemi iz REJECT runde su potvrđeno riješeni uživo,
ne samo u kodu. **Zaključak:** DENT-DESKTOP-E spremno za merge. Čeka
human approval (Radovan).
