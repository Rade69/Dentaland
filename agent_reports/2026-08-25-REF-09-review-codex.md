# REF-09 — Codex independent review (test kvalitet)

```yaml
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
blocking_findings:
  - F1: GUI testovi ne razlikuju Controller put od starog direktnog View -> Service poziva
```

## CILJ

Provjeriti da dashboard akcije „Potvrdi“ i „Odbaci“ stvarno idu kroz
`AppointmentController`, da „Odbaci“ ostaje bez dijaloga, da signalna
topologija nije promijenjena i da testovi genuinski zaključavaju novi
arhitektonski put.

## URAĐENO

- Potvrđeni worktree/grana
  `task/REF-09-dashboard-appointment-controller`, HEAD `0e00d4e` i ista
  pušovana remote grana.
- Diff prema base stanju pokazuje samo tri dozvoljena fajla:
  `desktop/controllers/appointment_controller.py`,
  `desktop/views/requests_panel.py` i implementer izvještaj. Forbidden paths
  nisu dirnuti.
- `requests_panel.py:147-151` na stvarnom commitu više nema
  `self.store.mark_confirmed`/`self.store.cancel`; oba handlera delegiraju u
  privatni `AppointmentController`.
- `AppointmentController.handle_appointment_action` ima odvojeni
  `"reject": "cancel"` u `method_map` (`appointment_controller.py:180-187`).
  Ranija `action == "cancel"` grana (`170-174`) ostaje dijalog-bazirana, dok
  `reject` ide kroz bezdijaloški store method poziv (`191-197`). UX zahtjev je
  zato ispunjen.
- Controller je konstruisan sa `_parent_widget=self`, gdje je `self`
  `DashboardPanels` (`requests_panel.py:31-33`). `confirm`/`reject` grana ne
  poziva `_doctors`, `_has_doctors` ni `_current_doctor_id`; ti helperi se
  koriste samo u create/edit tokovima (`appointment_controller.py:47-54,
  68-123`). Za ova dva action-a parent se koristi samo kao roditelj eventualnog
  `QMessageBox.warning`.
- `_on_appointment_changed` radi istim redoslijedom kao stari handleri:
  `self.refresh()` pa `self.changed.emit()` (`requests_panel.py:153-155`).
  Jedini produkcijski slušalac `dashboard_panels.changed` je
  `MainWindow._refresh_dashboard` (`main_window.py:142`), pa dashboard,
  scheduler i badge refresh topologija ostaju sačuvani.

## BLOCKING FINDING

### F1 — postojeći GUI testovi daju lažni PASS na starom direktnom putu

`test_klik_na_potvrdi_zove_mark_confirmed_i_uklanja_stavku` i
`test_klik_na_odbaci_zove_cancel_i_uklanja_stavku`
(`tests/test_gui/test_requests_panel.py:93-116`) provjeravaju samo krajnju
store evidenciju i osvježeni sadržaj panela. Ne provjeravaju da je pozvan
`AppointmentController.handle_appointment_action`, niti da View više nema
direktan mutacijski poziv.

Adversarna provjera je privremeno vratila tačno stari obrazac:

```python
def _confirm_scheduled(self, appt_id):
    self.store.mark_confirmed(appt_id)
    self.refresh()
    self.changed.emit()

def _cancel_scheduled(self, appt_id):
    self.store.cancel(appt_id)
    self.refresh()
    self.changed.emit()
```

Zatim su pokrenuta baš dva relevantna testa:

```text
2 passed, 1 warning in 0.14s
```

Dakle, test suite bi prihvatio povratak originalnog F4 nalaza koji REF-09
treba zatvoriti. Mutacija je nakon probe potpuno vraćena; produkcijski fajl
ponovo ima isti Git blob hash kao HEAD (`b63acb5...`).

Ovo je isti tip test-quality slabosti kao raniji REF-03 false-pass nalazi:
trenutni kod izgleda ispravno, ali nema regresijske sigurnosne mreže za
ključni acceptance invarijant. Zato review ostaje `REJECT` dok novi test ne
padne na direktnom View -> Service obliku.

Minimalan robustan test može monkeypatchovati
`panels._appointment_controller.handle_appointment_action`, kliknuti oba
dugmeta i potvrditi tačne pozive `(7, "confirm")` i `(7, "reject")`, dok
direktne store metode postavi da odmah bace grešku ako ih View pozove. Time
se istovremeno zaključavaju Controller ruta i bezdijaloški `reject` action.
Statička AST provjera odsustva mutacijskih `self.store.*` poziva može biti
dodatna zaštita, ali runtime delegacijski test treba biti primarni dokaz.

## STANDARDNA VERIFIKACIJA

Na čistom commitu `0e00d4e`, nakon vraćene mutacije:

```text
python -m pytest tests/ -q --basetemp=.tmp-ref09-full
355 passed, 11 warnings in 17.58s

ruff check src desktop backend tests --no-cache
All checks passed!

mypy src desktop backend --no-incremental
Success: no issues found in 50 source files
```

Prvi sandboxirani pokušaji pisanja pytest/Ruff/mypy cache-a u worktree izvan
glavnog writable roota završili su permission greškama; ponavljanje sa
odobrenim worktree pristupom dalo je gore navedene čiste rezultate.

## NE DIRATI

- Ne mijenjati `main_window.py`; privatna Controller instanca u
  `DashboardPanels` je eksplicitno ugovoreni scope.
- Ne preusmjeravati `reject` na postojeći `cancel_appointment()` dijalog-flow.
- Ne širiti task na REF-10/11/12 fajlove ili servisni sloj.
- Reviewer nije implementirao popravku testa.

## SLJEDEĆE

Implementer treba dodati runtime GUI test koji pada kada
`_confirm_scheduled`/`_cancel_scheduled` direktno pozovu store, ponoviti oba
mutaciona testa i standardnu verifikaciju, pa vratiti REF-09 Codexu na kratki
re-review. Claude review i Radovan human approval dolaze tek nakon Codex
PASS-a.
