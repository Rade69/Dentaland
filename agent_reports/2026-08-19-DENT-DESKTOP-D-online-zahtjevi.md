# Implementer izveštaj — DENT-DESKTOP-D (Faza D)

Task: DENT-DESKTOP-D | Risk: MEDIUM | Implementer: pi | Status: REVIEWED PASS — čeka human approval (vidi Review niže)

## Cilj faze

Zamijeniti generički `ConfirmationDialog` stilizovanim `ProcessRequestDialog`,
svesti pending karticu na jednu akciju "Obradi", i ukloniti izmišljeni
"Sljedeći slobodan termin" placeholder.

## Izmijenjeni fajlovi (svi u allowed_paths)

- `desktop/views/dialogs/process_request.py` (nov)
- `desktop/views/dialogs/base_dialog.py` (mod — reusable `add_footer_button`)
- `desktop/views/dialogs/__init__.py` (mod — export `ProcessRequestDialog`)
- `desktop/views/requests_panel.py` (mod)
- `tests/test_gui/test_process_request_dialog.py` (nov)
- `tests/test_gui/test_requests_panel.py` (mod — 3 nova testa)

## Šta je implementirano

- **`ProcessRequestDialog`** (BaseDialog-based, koristi B2 helpere):
  - read-only info sa ikonicama (`make_icon_label`): pacijent, telefon, email
    (samo ako postoji), željeni datum;
  - input: doktor (`QComboBox`), vrijeme (`QTimeEdit` — ručni izbor, BEZ lažnih
    slot dugmadi), usluga (`QComboBox`);
  - footer `[Odbij zahtjev] [Potvrdi termin]` preko novog `add_footer_button`
    (reusable u BaseDialog, bez automatskog accept/reject);
  - `selected_action()` → `"confirm"`/`"reject"`/`None` (X zatvaranje = None);
  - `values()` → `(doctor_id, service_id, start)` — isti oblik kao stari dialog.
- **`requests_panel.py`**:
  - uklonjen generički `ConfirmationDialog` (i nepotrebni importi);
  - pending kartica: JEDNO dugme **"Obradi"** umjesto para "Potvrdi | Odbij";
  - "Odbij" je sada unutar dijaloga (`selected_action == "reject"` → `reject_pending`);
  - uklonjen "Sljedeći slobodan termin" placeholder + "Napravi termin" stub;
  - dodat naslov sekcije "DANAS"; pending empty state → "Sve je obrađeno.";
  - "Čekaju potvrdu" (awaiting termini) ZADRŽAVA "Potvrdi"/"Odbaci" (nije request kartica).

## Šta namjerno NIJE urađeno

- Nema lažne dostupnosti/slot picker-a (nema pravog availability servisa).
- Nema "Sljedeći slobodan termin" (izmišljena funkcionalnost uklonjena).
- `main_window.py` nije diran (DashboardPanels je već ožičen — nije trebalo wiring-a).

## Verifikacija

```
pytest tests/test_gui/test_requests_panel.py tests/test_gui/test_process_request_dialog.py -v  → 14 passed
pytest tests/ -q  → 194 passed
ruff check desktop tests  → All checks passed!
mypy src/dentaland desktop backend  → 6 errors (baseline, nula novih)
```

## Scope potvrda

`git status` pokazuje izmjene samo u `allowed_paths`. Nijedan `forbidden_path`
nije diran — posebno `src/dentaland/**`, `week_view.py`, `sidebar.py`,
`appointment_dialog.py`.

## Review (Claude, Reviewer 1) — nezavisna provjera

```yaml
verdict: REJECT
scope: PASS
acceptance: FAIL
architecture: PASS
security: PASS
blocking_findings:
  - location: desktop/views/requests_panel.py, DashboardPanels._confirm()
    rule: "Task Contract (moja instrukcija prije implementacije) — 'confirm/reject must still... handle OverlapError/ValueError gracefully without crashing the UI'. Live repro: store.confirm_pending(...) poziv nakon dialog.exec() nema try/except — OverlapError propagira nehvaćen kroz Qt slot kad izabrani doktor/vrijeme kolidira sa postojećim terminom."
```

### Nezavisno provjereno

- `pytest tests/ -q` → 194 passed. `ruff check desktop tests` → All checks
  passed. `mypy src/dentaland desktop backend` → 6 grešaka, baseline, nula
  novih.
- `git diff --stat` — tačno `allowed_paths`. `base_dialog.py` diff pregledan
  red-po-red: **isključivo aditivna** nova metoda `add_footer_button()` —
  nijedna postojeća metoda (`add_primary_button`, `add_secondary_button`,
  `make_icon_label`, `add_outline_button`, `_apply_style`) nije dirana, pa
  Faza B/B2/C dijalozi (Editor/Details/Move/Cancel) nisu izloženi riziku
  regresije od ove izmjene. Widther-blast-radius briga je bila opravdana
  za provjeriti, ali nalaz je čist.
- `main_window.py` tvrdnja "nije trebalo wiring-a" — potvrđeno tačno:
  `DashboardPanels(store, self)` i `.changed.connect(self._refresh_dashboard)`
  već postoje na `main`-u, `_confirm()` i dalje zove `self.changed.emit()`
  na kraju (nepromijenjeno), pa signal lanac ostaje netaknut.
- Live screenshot `ProcessRequestDialog`-a (offscreen render, realni
  doktor/usluga podaci) — vizuelno tačno koristi B2 helpere
  (`make_icon_label` ikonice person/phone/mail/calendar u teal krugovima,
  `add_outline_button` crveni "Odbij zahtjev", primary teal "Potvrdi
  termin"), obično `QTimeEdit` (dropdown strelice, ne dugmad) — **potvrđeno
  da NE liči na lažni slot-picker**.
- `ProcessRequestDialog` sopstveni testovi (9 novih) su temeljiti i tačni
  — ali svi rade sa `SimpleNamespace`/tuple podacima, nijedan ne prolazi
  kroz `DashboardPanels._confirm()` orkestraciju sa pravim
  `AppointmentService`. Isto važi za 3 nova testa u `test_requests_panel.py`
  — koriste `DashboardStore` fake čiji `confirm_pending` nikad ne baca.
  Rupa u pokrivenosti je stvarna, ne samo teorijska mogućnost.

### Živa reprodukcija (adversarno, Korak 4)

Napravio sam pravi `AppointmentService` nad privremenom SQLite bazom,
kreirao postojeći termin (Dr Ljubo, 20.08. 09:00–09:30), zatim pravi
`DashboardPanels._confirm()` poziv sa web zahtjevom za isti dan, gdje
`ProcessRequestDialog` (monkeypatch samo da simulira klik na "Potvrdi
termin" sa doktorom=Ljubo, vrijeme=09:00 — namjerna kolizija):

```
REPRO: _confirm() raised UNCAUGHT OverlapError: potvrda se preklapa sa
postojećim aktivnim terminom istog doktora
REPRO: pending requests remaining after attempt: 1
```

Pozitivno: zahtjev ostaje ispravno PENDING (nije lažno označen kao
obrađen), podaci nisu oštećeni. Ali korisničko iskustvo je neuhvaćen
izuzetak — ništa vizuelno ne kaže osoblju "izaberi drugo vrijeme",
dijalog je već zatvoren kad se poziv desi. Ovo je realan, lako dostižan
scenario u svakodnevnoj upotrebi (osoblje bira vrijeme koje je već
zauzeto), ne egzotičan rub-slučaj.

### Zaključak

Arhitektura, scope disciplina i vizuelni rezultat su odlični — ovo NIJE
isti razred problema kao trivijalni fixevi iz B/B2 (jedna linija). Treba
stvarna restrukturacija toka, po istom obrascu koji već postoji u Fazi
B/C (`_edit_appointment`/`_move_appointment` u `main_window.py`): retry
petlja koja drži isti `ProcessRequestDialog` otvoren, hvata
`OverlapError`/`ValueError` i poziva `dialog.show_error(...)` (naslijeđeno
iz `BaseDialog`, `ProcessRequestDialog` ga već ima), umjesto da se
`store.confirm_pending(...)` poziva tek nakon što je dijalog zatvoren.

**Traženo prije ponovnog review-a:** restrukturirati
`DashboardPanels._confirm()` u petlju: dok god je akcija "confirm" i
`store.confirm_pending(...)` baci `OverlapError`/`ValueError`, pozvati
`dialog.show_error(str(exc))` i ponovo `dialog.exec()` (dijalog ostaje sa
istim izborom doktora/vremena/usluge da ih korisnik ne mora ponovo
unositi) — tek na uspjeh ili eksplicitni Odustani/X zatvoriti i
osvježiti. Dodati i test koji ovo pokriva sa pravim `AppointmentService`
(ne `DashboardStore` fake), po uzoru na
`tests/test_gui/test_main_window.py::test_overlap_greska_se_prikazuje_u_dijalogu_i_ne_zatvara_ga`
iz Faze B.

## Re-verifikacija poslije fix-a (Claude) — PASS

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

- `pytest tests/ -q` → 195 passed (194 + 1 novi test). `ruff check desktop
  tests` → All checks passed. `mypy src/dentaland desktop backend` → 6
  grešaka, baseline, nula novih.
- Diff `_confirm()` odgovara traženoj retry-petlji tačno.

### Važna ispravka koju je implementer sam pronašao (ne ja)

Moja instrukcija u fix promptu je predložila
`from dentaland.services import OverlapError` (isti import kao u
`main_window.py`). To je **bilo pogrešno** — to je `booking.OverlapError`.
`confirm_pending()` → `confirm_request()` u `requests.py` baca **svoju
lokalnu, namjerno dupliranu** `OverlapError` klasu (definisanu u
`requests.py:30`, ne istu klasu kao `booking.py:113` — dvije odvojene
klase istog imena, ne alias). Da je implementer slijepo pratio moju
instrukciju, `except (OverlapError, ValueError)` bi izgledao ispravno u
kodu ali NE BI stvarno hvatao ono što se baca — isti bug bi preživio,
samo sakriven iza koda koji izgleda popravljeno.

Implementer je umjesto toga uvezao `from dentaland.services.requests
import OverlapError` sa jasnim komentarom zašto, i to sam nezavisno
provjerio direktno u izvornom kodu (`requests.py:141` zaista baca
lokalnu klasu) — implementerova verzija je ispravna, moja predložena
nije bila.

### Živa re-reprodukcija (moj originalni repro, prilagođen retry obrascu)

Isti scenario kao u REJECT rundi (postojeći termin kod Dr. Ljube 09:00,
pokušaj potvrde kolidirajućeg zahtjeva), ovaj put kroz kompletan tok:

```
REPRO: _confirm() completed without an uncaught exception
REPRO: exec() called 2 times (expect 2: overlap-fail then reject)
REPRO: inline errors shown: ['potvrda se preklapa sa postojećim aktivnim terminom istog doktora']
REPRO: pending requests remaining after attempt: 0
```

Nema neuhvaćenog izuzetka, dijalog se stvarno ponovo otvorio (2 exec
poziva), inline greška se stvarno prikazala sa tačnom porukom, i zahtjev
je na kraju ispravno obrađen (odbijen u ovom scenariju) — ne zaglavljen
u limbu.

**Zaključak:** DENT-DESKTOP-D potpuno spremno za merge. Implementerova
sopstvena dijagnoza i ispravka `OverlapError` importa (van onoga što sam
ja tražio) je vrijedna posebno pomenuti — to je tačno onaj nivo
provjere koji ovaj proces traži od implementera, ne samo slijepo
izvršavanje review komentara. Čeka human approval (Radovan).
