---
task_id: FIX-04
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: ASSIGNED — dodijeljeno Pi-ju (implementer)
created_at: 2026-08-21
---

# FIX-04 — Ne gutati ValueError bez feedbacka

## Task Contract

**Cilj:** `MainWindow` trenutno na tri mjesta radi
`with suppress(ValueError): method(...)` — ako servisna operacija ne
uspije (npr. pokušaj da se potvrdi već otkazan termin), korisnik ne
dobije nikakvo objašnjenje, akcija se tiho ne desi.

**Risk:** MEDIUM (dira glavni appointment action dispatch, korišten
konstantno)

**Izvor:** `docs/dentaland-desktop-korektivni-plan.md`, sekcija 5
(PRIORITET 5). Pun kontekst korektivnog plana (FIX-01 do FIX-06) tamo —
ovaj task pokriva SAMO FIX-04, ne šire.

## Root cause (već lociran, ne treba ponovo istraživati) — tačno 3 mjesta

`desktop/views/main_window.py`:

1. **Linija 767** — `_handle_appointment_action`, `method_map` dispatch
   (`confirm`/`arrived`/`unarrived`/`completed`/`no_show`):
   ```python
   method = getattr(self.store, method_name, None)
   if callable(method):
       with suppress(ValueError):
           method(appt_id)
   self._refresh_dashboard()
   ```
2. **Linija 790** — `_cancel_appointment`:
   ```python
   cancel_fn = getattr(self.store, "cancel", None)
   if callable(cancel_fn):
       with suppress(ValueError):
           cancel_fn(appt.id)
   self._refresh_dashboard()
   ```
3. **Linija 800** — `_delete_appointment`:
   ```python
   delete_fn = getattr(self.store, "delete", None)
   if callable(delete_fn):
       with suppress(ValueError):
           delete_fn(appt.id)
   self._refresh_dashboard()
   ```

**Servisni sloj (`src/dentaland/services/booking.py`) već baca čiste,
korisniku razumljive poruke** — ne treba ih prepisivati, samo prestati
ih gutati:

- `mark_confirmed`/`mark_arrived`/`mark_completed`/`mark_no_show`: `"termin
  {id} nije pronađen"` ili `"samo zakazan termin može biti označen kao
  <status>"`.
- `cancel`: `"termin {id} nije pronađen"` ili `"samo zakazan termin može
  biti otkazan"`.
- `delete`: `"termin {id} nije pronađen"` (bez status-provjere, po
  dizajnu iz DENT-DESKTOP-F).

Kontrakt dozvoljava korištenje ovih poruka direktno (`str(exc)`) — "Ako
postojeći service `ValueError` već ima čistu user-facing poruku, može
se koristiti." Ne izmišljati novi tekst, ne prepisivati servisni sloj.

## Zašto QMessageBox, ne inline error label

`blockout_panel.py`/`settings_panel.py` već imaju uspostavljen `except
ValueError as exc: self._show_error(str(exc))` obrazac sa PERZISTENTNIM
inline error QLabel-om — to radi jer su to fiksni formulari. Sva tri
mjesta u `main_window.py` su OKINUTA iz context-menija ili već-zatvorenog
potvrdnog dijaloga (nema fiksnog mjesta za inline poruku vezano za
kliknuti red/ćeliju u kalendaru). Zato je `QMessageBox.warning(self,
"<naslov>", str(exc))` ovdje ispravan minimalan izbor — ne izmišljati
novi custom toast/snackbar mehanizam za ovaj task (van obima).
`QMessageBox` nije trenutno uvezen u `main_window.py` — dodati import.

## Šta uraditi

Za svako od tri mjesta: zamijeniti `with suppress(ValueError): ...`
sa `try/except ValueError as exc:` koji poziva
`QMessageBox.warning(self, "<naslov>", str(exc))`, zatim NASTAVITI na
`self._refresh_dashboard()` (van try/except, nepromijenjeno — refresh
se dešava bez obzira na ishod, isto kao i sada).

Predložen minimalan oblik (mjesto 1, `method_map` dispatch):

```python
method = getattr(self.store, method_name, None)
if callable(method):
    try:
        method(appt_id)
    except ValueError as exc:
        QMessageBox.warning(self, "Akcija nije uspjela", str(exc))
self._refresh_dashboard()
```

Analogno za `_cancel_appointment` (naslov npr. "Otkazivanje nije
uspjelo") i `_delete_appointment` (naslov npr. "Brisanje nije uspjelo").
Implementer bira tačan tekst naslova — mora biti kratak i nedvosmislen,
ne mora biti identičan ovom prijedlogu.

**Ne prikazivati traceback ni Python exception repr** — samo
`str(exc)` (servisna poruka je već čista, provjereno gore).

## Allowed paths

```text
desktop/views/main_window.py
tests/test_gui/test_main_window.py
```

## Forbidden paths

```text
src/dentaland/models.py
migrations/
src/dentaland/services/booking.py
desktop/views/week_view.py
desktop/views/day_view.py
desktop/views/dialogs/**
desktop/views/blockout_panel.py
desktop/views/settings_panel.py
```

## Obavezni regression testovi

1. Neuspješna status-akcija prikazuje poruku, ne ruši aplikaciju:
   ```text
   termin u statusu CANCELLED (ili COMPLETED)
   pozvati _handle_appointment_action(id, "confirm")
   QMessageBox.warning pozvan sa servisnom porukom (mockovati
   QMessageBox.warning, ne stvarno otvarati modal u testu — isti
   obrazac kao ostali GUI testovi ove sesije koji izbjegavaju stvarne
   blokirajuće Qt modale)
   scheduler ostaje stabilan (nema exception-a koji izlazi iz metode)
   ```
2. Neuspješan `cancel` na već-otkazanom/terminalnom terminu prikazuje
   poruku, ne ruši aplikaciju.
3. Neuspješan `delete` na nepostojećem ID-u prikazuje poruku (rijedak
   slučaj u praksi jer UI obično ne nudi akciju na nepostojeći termin,
   ali servis to i dalje baca — pokriti da regresija ne uđe).
4. **Regresija — uspješna akcija i dalje radi identično kao prije**:
   postojeći testovi `test_context_action_confirm_poziva_mark_confirmed`,
   `test_context_action_completed_osvjezava_status_summary`,
   `test_delete_akcija_trajno_uklanja_termin_kroz_pravi_servis`,
   `test_delete_odustani_ne_brise_termin` ne smiju regresirati — uspješan
   put se ne dira, samo neuspješan.

## Acceptance criteria

- [ ] Nijedna od tri appointment akcije ne guta `ValueError` u tišini.
- [ ] Poruka je servisna poruka (`str(exc)`), bez traceback-a.
- [ ] UI ostaje stabilan (nema pucanja) i nakon neuspješne akcije.
- [ ] Scheduler se osvježava i nakon greške (nepromijenjeno ponašanje).
- [ ] Uspješan put (akcija prođe) ostaje identičan — nula regresije.
- [ ] Nema izmjena van `allowed_paths`, posebno nema izmjena u
      `booking.py` (servisne poruke se ne prepisuju).

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline za poređenje (izmjereno 21.8.2026 na `main` nakon `FIX-03`):
pytest 269 passed, ruff clean, mypy clean (0 issues, 35 fajlova).

## Review

Claude, nezavisan od implementera. MEDIUM risk — po tabeli u
`docs/dentaland-agentski-razvoj.md` human approval (Radovan) JE
obavezan prije merge-a.

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim` na
`desktop/views/main_window.py`. Radi u zasebnom git worktree
(`Dentaland-worktrees/FIX-04-<slug>`, grana `task/FIX-04-<slug>`).
