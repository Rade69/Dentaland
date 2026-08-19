# Implementer izveštaj — DENT-DESKTOP-C (Faza C)

Task: DENT-DESKTOP-C | Risk: MEDIUM | Implementer: pi | Status: REVIEWED PASS_WITH_NOTES — čeka human approval

## Cilj faze

Operativni model rada sa postojećim terminom: lijevi klik → Detalji, desni klik →
status-aware brze akcije, drag&drop ostaje, pomjeranje/otkazivanje kroz stilizovane
modale. WeekView postaje "glup" (emituje signale), MainWindow orkestrira store pozive.

## Izmijenjeni fajlovi (svi u allowed_paths)

- `desktop/views/week_view.py` (mod — novi signali, status-aware context menu)
- `desktop/views/main_window.py` (mod — orkestracija akcija)
- `desktop/views/dialogs/appointment_details.py` (nov)
- `desktop/views/dialogs/move_appointment.py` (nov)
- `desktop/views/dialogs/cancel_appointment.py` (nov)
- `desktop/views/dialogs/__init__.py` (mod — export novih dialoga)
- `tests/test_gui/test_week_view.py` (mod)
- `tests/test_gui/test_main_window.py` (mod)
- `tests/test_gui/test_appointment_details_dialog.py` (nov)
- `tests/test_gui/test_destructive_dialogs.py` (nov)

## Šta je implementirano

- **WeekView** (glup sloj — ne poziva store direktno):
  - `appointment_clicked = Signal(int)` — lijevi klik na termin emituje ID;
    prazan slot i dalje emituje `slot_selected` (postojeće ponašanje).
  - `appointment_action_requested = Signal(int, str)` — status-aware context menu:
    - uvijek "Otvori detalje";
    - za aktivni termin: "Potvrdi termin" (samo ako nije potvrđen), "Pacijent je
      stigao"/"Poništi (nije stiglo)", "Označi kao završen", "Označi 'nije došao'",
      "Uredi termin", "Pomjeri termin", "Otkaži termin";
    - terminalni (COMPLETED/NO_SHOW/CANCELLED): samo "Otvori detalje".
  - uklonjene `mark_appointment_arrived`/`unmark_appointment_arrived`/`_call_status_method`
    (store pozivi su prešli u MainWindow).
- **AppointmentDetailsDialog**: read-only prikaz (ime/telefon/email/datum/vrijeme/
  trajanje/doktor/usluga/napomena) + status badge + uslovne akcije. Status NIJE
  dropdown (nema QComboBox). Terminalni nema povratnih akcija. `selected_action()`
  vraća izabranu akciju.
- **MoveAppointmentDialog**: trenutno vrijeme + novi datum/vrijeme/trajanje (trajanje
  se čuva iz `end - start`); `get_data()` → `(novi_start, trajanje_min)`.
- **CancelAppointmentDialog**: pacijent + vrijeme + "Otkazani termin ostaje sačuvan
  u istoriji" (bez razloga otkazivanja). Destructive dugme.
- **MainWindow** (orkestrator):
  - `appointment_clicked` → `_open_appointment_details`;
  - `appointment_action_requested` → `_handle_appointment_action` (switch po akciji):
    - `confirm`/`arrived`/`unarrived`/`completed`/`no_show` → odgovarajuća store metoda
      (`mark_confirmed`/`mark_arrived`/`unmark_arrived`/`mark_completed`/`mark_no_show`);
    - `edit` → `_edit_appointment` (iz Faze B, kroz `store.update`);
    - `move` → `_move_appointment` (inline overlap, modal ostaje otvoren);
    - `cancel` → `_cancel_appointment` (kroz `store.cancel`);
    - svaka akcija → `_refresh_dashboard` (status summary se osvježava).

## Šta namjerno NIJE urađeno

- Hard delete (Faza F, HIGH, zasebno) — "Otkaži termin" je cancel (zapis ostaje).
- Razlog otkazivanja (šema ga ne čuva).
- Restore/reopen iz terminalnih stanja.

## Verifikacija

```
pytest tests/test_gui/test_week_view.py tests/test_gui/test_main_window.py \
       tests/test_gui/test_appointment_details_dialog.py tests/test_gui/test_destructive_dialogs.py -v  → 48 passed
pytest tests/ -q  → 184 passed
ruff check desktop tests  → All checks passed!
mypy src/dentaland desktop backend  → 6 errors (baseline, nula novih)
```

mypy 6 grešaka = baseline (appointment_dialog.py stara greška je već uklonjena u
Fazi B; nijedna nova iz ove faze — svi novi parametri su tipovani).

## Scope potvrda

`git status` pokazuje izmjene samo u `allowed_paths`. Nijedan `forbidden_path`
nije diran — posebno `src/dentaland/**` (servisni sloj), `dialogs/appointment_editor.py`
i `dialogs/base_dialog.py` (iz Faze B, read-only ovdje).

## Review (Claude, Reviewer 1) — nezavisna provjera

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

### Nezavisno provjereno

- `pytest tests/ -q` → 184 passed (potvrđeno).
- `ruff check desktop tests` → All checks passed.
- `mypy src/dentaland desktop backend` → **6 grešaka**, tačno na baseline
  uspostavljen poslije Faze B (ne 7 — implementer je ispravno primijenio
  lekciju iz prošlog review-a).
- `git diff --stat` / scope potvrđen — tačno `allowed_paths`, nula dodira
  `forbidden_paths`, `appointment_editor.py`/`base_dialog.py` iz Faze B
  zaista netaknuti.
- Zaključane odluke iz plana (sekcija 0) provjerene u kodu, ne samo u
  izvještaju: status NIJE dropdown (potvrđeno — `AppointmentDetailsDialog`
  nema `QComboBox`, samo badge + uslovna dugmad); nema polja za razlog
  otkazivanja (`CancelAppointmentDialog` provjeren red-po-red); statusni
  summary ostaje i osvježava se (potvrđeno uživo, vidi niže); hard delete
  se nigdje ne pojavljuje (`grep -rn "Izbriši\|delete("` u novim fajlovima
  → prazno); drag & drop mehanika (`dropEvent`, `move_appointment_to_slot`)
  netaknuta.

### Živa reprodukcija (pravi `MainWindow` + pravi `AppointmentService`, ne mock)

- **REPRO 0** — pravi signal `appointment_clicked.emit()` → pravi
  `AppointmentDetailsDialog.exec()` (monkeypatch samo da simulira klik na
  "Potvrdi termin" dugme, ne da zaobiđe stvarni tok) → `confirmed_at` je
  stvarno postavljen. Pun put od lijevog klika do store poziva radi.
- **REPRO 1** — poslije "confirm" akcije, `status_legend.text()` sadrži
  "Potvrđen (1)" — statusna traka se STVARNO osvježava, ne samo po tvrdnji
  iz izvještaja.
- **REPRO 2 (adversarno)** — kad je termin već "stigao", `AppointmentDetailsDialog`
  nudi: `['Potvrdi termin', 'Označi kao završen', "Označi 'nije došao'",
  'Uredi termin', 'Pomjeri termin', 'Otkaži termin']` — **NEMA "Poništi
  (nije stiglo)"**. Context meni (desni klik) TU akciju ima (potvrđeno u
  `week_view.py` diff-u, i `unarrived` je ožičen u `_handle_appointment_action`)
  — dva ulazne tačke za istu operaciju nisu simetrična. Nije eksplicitno
  traženo u planu da budu identične, ali je stvarna, nenamjerna
  nekonzistentnost (nije spomenuto ni u izvještaju implementera).
- **REPRO 3 (adversarno)** — akcija na terminu koji je u terminalnom stanju
  (`mark_completed`, pa ponovo `confirm`): `store.mark_confirmed()` baca
  `ValueError`, `_handle_appointment_action` ga hvata sa `suppress(ValueError)`
  i **ništa se ne prikazuje korisniku** — ni greška, ni potvrda, tiho ništa.
  Status ostaje ispravno nepromijenjen (nema oštećenja podataka), ali
  korisnik nema nikakav znak da klik nije uspio. Ovo je isti obrazac
  "tiha neuspjela akcija" koji smo ranije ovu sesiju popravljali na web
  formi (nedostatak povratne informacije) — ovdje je rizik veći otkad
  postoji 20s auto-refresh tajmer koji može promijeniti stanje termina
  između otvaranja menija i klika (race prozor), pa ova putanja nije
  čisto teoretska.

### Zaključak

Nijedan nalaz ne krši eksplicitnu acceptance stavku iz plana — oba su
otkrivena adversarnim testiranjem (Korak 4), ne kršenjem ugovora. `PASS_WITH_NOTES`
umjesto `PASS`: preporučujem da se oba zavedu kao follow-up (mogu ući u
istu fazu brzim dopunom, ili u kasniju polish rundu) prije nego se
zaboravi:

1. Dodati "Poništi (nije stiglo)" akciju u `AppointmentDetailsDialog` kad
   je `arrived_at` već postavljen (simetrija sa context menijem).
2. Dati vidljivu povratnu informaciju (makar kratak status bar red ili
   `QMessageBox`) kad `_handle_appointment_action` uhvati `ValueError`,
   umjesto tihog `suppress`.

Nijedno nije blokirajuće za merge ove faze — oba su mali, izolovani
follow-up, ne zahtijevaju redizajn.
