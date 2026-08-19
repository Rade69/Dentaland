# Implementer izvještaj — DENT-DESKTOP-F (hard delete termina, HIGH)

Task: DENT-DESKTOP-F | Risk: HIGH | Implementer: Claude (direktno) | Status: IMPLEMENTED — čeka Reviewer 1/2 (Crush, Pi)

## Cilj

Faza F (6/6, posljednja faza redizajna) — trajno, nepovratno brisanje
termina, isključivo za greškom kreiran zapis. Vidi puni plan (napisan
PRIJE koda, po HIGH-risk proceduri) u `agent_reports/2026-08-19-DENT-DESKTOP-F-plan.md`.

## Fact found — FK/cascade (F.3, prije koda)

`src/dentaland/models.py` pregledan u cijelosti: `Appointment` ima FK-ove
KA `Doctor`/`Service` (ne obrnuto). `grep -n "appointments.id" models.py`
→ prazno. Nijedna tabela ne referencira `appointments.id`. Zaključak:
prost `session.delete(appt)` je siguran bez cascade rizika. Ovo je
provjereno statičkom analizom PRIJE pisanja koda, i dodatno potvrđeno
testom (`test_delete_ne_dira_druge_termine` — kreirana dva termina,
obrisan jedan, drugi ostaje netaknut na realnoj test bazi).

## Decision required — RIJEŠENO

Radovan je (AskUserQuestion, 19.8.2026) potvrdio: "Izbriši termin"
dostupno za SVE statuse, uključujući terminalne. Implementirano u skladu
s tim — vidi ispod.

## Izmijenjeni/novi fajlovi (svi u allowed_paths)

- `src/dentaland/services/booking.py` — `delete(appt_id) -> None`, bez
  status-provjere (radi za bilo koji status).
- `desktop/views/dialogs/delete_appointment.py` (nov) — `DeleteAppointmentDialog`.
- `desktop/views/dialogs/__init__.py` — export.
- `desktop/views/dialogs/appointment_details.py` — dugme "Izbriši termin",
  UVIJEK vidljivo (i za terminalne termine, van `if not terminal:` bloka),
  vizuelno odvojeno (`addSpacing(6)` + poseban crveni-obrisani stil, van
  "Operativne akcije" sekcije).
- `desktop/views/week_view.py`, `desktop/views/day_view.py` — "Izbriši
  termin" iza posebnog `addSeparator()` na dnu context menija, UVIJEK
  prisutno (van `if not terminal:` bloka). `day_view.py` nije bio u
  originalnom F.2 spisku putanja (plan je pisan prije Faze E) — dodat
  radi konzistentnosti sa week_view.py (isti akcioni set svuda drugdje
  već postoji u oba fajla od Faze E), dokumentovano u plan fajlu.
- `desktop/views/main_window.py` — `_handle_appointment_action` grana za
  `"delete"`, novi `_delete_appointment(appt)` (isti orkestracioni
  obrazac kao `_cancel_appointment`).
- `tests/test_services.py` — 4 nova testa za `delete()`.
- `tests/test_gui/test_destructive_dialogs.py` — 3 nova testa (prikaz,
  Enter-safety, accept selektuje akciju).
- `tests/test_gui/test_appointment_details_dialog.py` — 2 nova testa +
  1 IZMIJENJEN postojeći test (`test_terminalni_termin_nema_povratnih_akcija`
  je prije očekivao PRAZNU listu akcija za terminalni termin — sad
  ispravno očekuje `["Izbriši termin"]`, jer je to namjerna, odobrena
  promjena ponašanja ove faze, ne regres).
- `tests/test_gui/test_week_view.py`, `test_day_view.py` — po 1 novi test
  (signal wiring za "delete" akciju).
- `tests/test_gui/test_main_window.py` — 2 nova testa (delete kroz pravi
  `AppointmentService`: accept stvarno briše, reject/X ne briše ništa).

## Enter-safety (F.4 zahtjev)

`DeleteAppointmentDialog`-ovo "Izbriši termin" dugme eksplicitno ima
`setAutoDefault(False)` i `setDefault(False)` — jedina namjerna razlika
od `BaseDialog.add_primary_button`-ovog inače uobičajenog ponašanja u
cijelom redizajnu (dokumentovano unaprijed u plan fajlu prije koda).
Pokriveno testom `test_delete_dugme_ne_reaguje_na_enter`.

## Greška uočena i ispravljena tokom rada (transparentnost)

Prvobitna verzija testa `test_kontekst_meni_nudi_izbrisi_termin`
(week_view) je koristila `monkeypatch.setattr(QMenu, "exec", ...)` da
presretne stvarni modal poziv — isti obrazac koji je RANIJE ovu sesiju
(Faza C review) već pokazao da ne radi pouzdano u ovoj PySide6 verziji
(monkeypatch ne presreće stvarni C++ nivo poziv, izazivajući pravu
blokirajuću modalnu petlju). Test je stvarno zaglavio pri pokretanju
(`pytest` timeout na 33% suite-a), potvrđeno `ps`/`Get-CimInstance`
pregledom procesa (PID 22056, `python -m pytest tests/ -q`, ubijen
ciljano preko PowerShell-a, bez diranja korisnikovog `dev_local.py`/
uvicorn/http.server procesa koji su ostali netaknuti). Uklonjen taj
test — zamijenjen sa `test_izbrisi_termin_emituje_delete_akciju`, koji
NE zavisi od `.exec()` presretanja (gradi `QMenu()` direktno i okida
`QAction.trigger()`), isti obrazac koji je RANIJE ovu sesiju već
verifikovan kao pouzdan.

## Verifikacija

```
pytest tests/ -q                              → 215 passed
ruff check src/dentaland desktop tests        → All checks passed!
mypy src/dentaland desktop backend            → 6 errors (baseline, nula novih)
```

### Živa reprodukcija (offscreen Qt + prava SQLite baza, ne mock)

Kreirana dva termina (jedan aktivan, jedan namjerno prebačen u CANCELLED
— terminalno stanje), obrisan CANCELLED termin kroz pravi
`MainWindow._handle_appointment_action(id, "delete")` (dialog
monkeypatch samo da simulira klik na "Izbriši termin", ne da zaobiđe
stvaran store poziv):

```
BEFORE: appointments in DB: 2
AFTER deleting terminal appt: appointments in DB: 1
  dto1 still present: True
  dto2 (deleted) gone: True
  dto2 absent from WeekView visible appts: True
  dto1 present in WeekView visible appts: True
```

Potvrđeno uživo: delete radi za terminalni status (Radovanova odluka),
drugi termin netaknut, WeekView prikaz se ispravno osvježava (obrisan
termin nestaje, drugi ostaje).

## Scope potvrda

`git status`/`git diff --stat` pokazuju izmjene isključivo u
`allowed_paths`. `models.py`, `migrations/`, `base_dialog.py`,
`appointment_editor.py`, `move_appointment.py`, `cancel_appointment.py`,
`process_request.py`, `requests_panel.py`, `sidebar.py` — sve netaknuto.

## Odbačene opcije

Vidi plan fajl (soft delete, cascade FK, nova "trash" ikonica) — sve
odbačeno prije koda, obrazloženo tamo.

## Sljedeći korak

Čeka nezavisan review od **Crush** i **Pi** (Reviewer 1/2, HIGH tok) —
ja (Claude, implementer) se ne vraćam da sam sebe pregledam u istom
kontekstu. Nakon oba reviewa, Radovan daje human approval prije merge-a.
