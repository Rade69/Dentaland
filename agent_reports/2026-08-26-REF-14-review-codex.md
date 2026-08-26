# REF-14 — Codex independent review (test kvalitet)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## CILJ

Provjeriti uklanjanje stringly-typed doctor-state čitanja iz
`AppointmentController`, kompatibilnost sva četiri konstruktorska poziva i
sigurno uklanjanje mrtvog `ScheduleController._current_doctor_id` polja.

## URAĐENO

- Potvrđeni lokalni i remote HEAD `6e3e37f` na grani
  `task/REF-14-doctor-state-providers`.
- `git diff --stat ce960d3..6e3e37f`: četiri fajla — implementer izvještaj i
  tačno tri dozvoljena produkcijska fajla:
  `appointment_controller.py`, `schedule_controller.py`, `main_window.py`.
- `day_view.py`, `week_view.py`, `requests_panel.py` i svi ostali forbidden
  paths nisu dirani.
- `pytest tests/ -q`: **374 passed**, 11 warnings.
- Ciljani `test_appointment_controller.py` + `test_main_window.py`:
  **37 passed**.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`:
  **All checks passed**.
- `mypy src/dentaland desktop backend`: **Success**, 52 source fajla.
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.

### Provider semantika i četiri konzumenta

Sva četiri produkcijska mjesta konstrukcije su pronađena i provjerena:

- `MainWindow` eksplicitno prosljeđuje sva tri provider callable-a;
- `DayView`, `WeekView` i `DashboardPanels` zadržavaju postojeći troargumentni
  poziv i koriste keyword-only default providere.

MainWindow postavlja `_current_doctor_id`, `_has_doctors` i `_doctors` prije
konstrukcije `AppointmentController`. Provideri su lambda-e i čitaju aktuelne
vrijednosti tek kada `on_slot_selected` ili `edit_appointment` zatraže state;
ne hvataju inicijalne vrijednosti. Runtime proba sa promjenjivim state-om
potvrdila je oba očitanja prije i poslije izmjene (`PROVIDER_LATE_BINDING_OK`).

Tri default konzumenta ne pozivaju doctor-state workflow. Njihovi defaulti
vraćaju `[]`, `False`, `None`, odnosno iste vrijednosti koje je stari
`getattr(..., default)` vraćao kad odgovarajući atribut ne postoji. Njihovi
pozivi i testovi ostaju nepromijenjeni i puni suite prolazi.

### Doctor workflow

`AppointmentController` više nema nijedan
`getattr(self._parent_widget, "_doctors"/"_has_doctors"/
"_current_doctor_id")` poziv. Jedini čitaoci su i dalje:

- `on_slot_selected`: lista doktora, trenutni doktor i validacija izbora;
- `edit_appointment`: lista doktora i validacija izbora.

Postojeći controller/MainWindow GUI testovi pokrivaju kreiranje, doctor izbor,
retry na overlap i dialog workflow; svih 37 ciljanih testova prolazi sa novim
provider čitanjem.

### Uklanjanje ScheduleController polja

Nezavisni grep nad pre-task commitom `ce960d3` pronašao je samo:

1. deklaraciju `self._current_doctor_id = None`;
2. assignment u `set_doctor_filter`.

Nema čitanja tog polja ni u `desktop/` ni u `tests/`. Stvarno ponašanje filtera
i dalje ide kroz `self._week_view.set_filter(doctor_id)` pa `self.refresh()`;
obje linije su netaknute. Uklanjanje je zato behavior-neutralno.

## NAPOMENA

Formulaciju „default provideri su identični starom getattr ponašanju“ treba
čitati precizno: identične su **fallback vrijednosti**, ali novi controller
namjerno više neće automatski pročitati doctor atribute sa proizvoljnog parent
objekta koji ih ima, a nije proslijedio providere. To je upravo cilj uklanjanja
implicitnog ugovora. Sva poznata produkcijska mjesta su provjerena: jedini
takav konzument (`MainWindow`) sada eksplicitno prosljeđuje providere, dok ih
ostala tri ne koriste. Zato ovo nije blocking nalaz.

## NE DIRATI

- Ne vraćati doctor-state `getattr` fallback; time bi se obnovio implicitni
  Controller→View ugovor koji REF-14 uklanja.
- Ne mijenjati `_parent_widget` weakref: ostaje potreban za Qt parenting.
- Ne mijenjati DayView/WeekView/DashboardPanels samo radi prosljeđivanja
  providera koje njihovi workflow-i ne koriste.

## SLJEDEĆE

Codex test-quality verdict je **PASS_WITH_NOTES**, bez blocking nalaza. Claude
sada radi Reviewer 2 arhitektonski pregled; Radovan human approval dolazi tek
nakon oba review-a.
