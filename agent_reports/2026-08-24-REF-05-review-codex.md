# REF-05 — Codex independent review (test kvalitet)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## CILJ

Nezavisno provjeriti da REF-05 stvarno svodi scheduler refresh na jedan
snapshot, ne renderuje skriveni view, čuva usklađen doctor state i da izmjene
postojećih GUI testova nisu oslabile njihove invarijante.

## URAĐENO

- Potvrđeni grana `task/REF-05-schedule-controller`, commit `7692f31` i base
  `daf3074` kao ancestor.
- Početni review na `7692f31`: `pytest tests/ -q` dao je **347 passed**.
- F1 re-review na fix commitu `8693264`: `pytest tests/ -q` dao je
  **349 passed**, 11 warnings.
- `ruff check src/dentaland desktop backend tests`: čist.
- `mypy src/dentaland desktop backend`: čist, 43 source fajla.
- Scope odgovara Task Contractu. Promijenjeni su samo novi ScheduleController,
  MainWindow, Day/Week view, tri pripadajuća postojeća test fajla, novi
  controller test i agent reports. Forbidden paths nisu dirani.

### F1 — riješeno u `8693264`

Početna verzija `tests/test_gui/test_schedule_controller.py` na `7692f31`
instancirala je Controller isključivo sa `_FakeView`. Taj fake samo je spremao
proslijeđeni dataset i nije izvršavao stvarni `WeekView.render_schedule()` ili
`DayView.render_schedule()`.

Adversarna mutacija:

1. U stvarni `WeekView.render_schedule()` privremeno je dodat direktan
   `store.appointments_for_range(...)`, čime se refresh vraća sa jednog na dva
   appointments fetcha za aktivni week view.
2. Pokrenut je `pytest tests/test_gui/test_schedule_controller.py -q`.
3. Stvarni rezultat: **6 passed in 0.07s**.
4. Mutacija je potpuno vraćena.

Fix je dodao dva integracijska query-counter testa koji koriste stvarne
`WeekView`, `DayView`, `QStackedWidget` i `ScheduleController`. Codex je
nezavisno ponovio obje mutacije:

1. Dodat interni `appointments_for_range(...)` u stvarni
   `WeekView.render_schedule()`: ciljani test je pao na **`assert 2 == 1`**.
2. Dodat isti interni fetch u stvarni `DayView.render_schedule()` (uz potreban
   `timedelta` import da mutacija bude validna): ciljani test je pao na
   **`assert 2 == 1`**.
3. Obje mutacije su vraćene; čisti
   `pytest tests/test_gui/test_schedule_controller.py -q` dao je **8 passed**.

Novi testovi sada genuinski hvataju regresiju u obje konkretne view klase, pa
je originalni blocking finding zatvoren.

### Doctor state

Normalna UI putanja trenutno ostaje sinhronizovana. `_on_tab_changed()` u
jednom sinhronom pozivu postavlja `MainWindow._current_doctor_id`, zatim zove
`ScheduleController.set_doctor_filter()`, koji postavlja svoju kopiju i
WeekView filter. Privremeni integracijski test nakon promjene taba potvrdio je
istu vrijednost u:

- `MainWindow._current_doctor_id`;
- `ScheduleController._current_doctor_id`;
- vrijednosti koju čita `AppointmentController._current_doctor_id()`;
- `WeekView._filter_doctor_id`.

Test je prošao i potom je uklonjen. Duplikacija je tehnički dug, ali u
postojećoj jedinoj UI putanji nije reproduciran funkcionalni bug.

### Drag-and-drop granica

Direktan `store.move(...)` u `WeekView` i `DayView` postojao je na base
commitu prije REF-05. Ovaj task ga nije uveo. REF-05 je samo zamijenio lokalni
`self.refresh()` signalom `appointment_moved`, koji MainWindow spaja na
`ScheduleController.refresh()`. Time postojeći dug nije proširen novom
servisnom mutacijom; premještanje te akcije u AppointmentController ostaje
van ovog taska.

### Mehaničke izmjene GUI testova

Uzorkovane izmjene u `test_week_view.py`, `test_day_view.py` i
`test_week_view_combined.py` zadržavaju iste podatke, akcije i očekivanja, a
`refresh()` zamjenjuju helperom koji fetchuje snapshot i poziva
`render_schedule()`. Posebno,
`test_prevlacenje_termina_azurira_vrijeme` i dalje provjerava oba invarijanta:
persistirano novo vrijeme i premještanje kartice sa stare na novu ćeliju.
Dodatni render poslije move-a simulira controller refresh koji test samog
view-a nema.

### Skriveni view

`ScheduleController.refresh()` uzima samo `view_stack.currentWidget()`, radi
jedan snapshot i poziva `render_schedule()` samo na tom objektu. Drugi view se
ne poziva. Postojeći fake-view test korektno hvata ovu orchestration osobinu,
ali, kako pokazuje F1, ne pokriva interne fetch regresije konkretnih view
klasa.

## NE DIRATI

- Ne mijenjati produkcijsku ScheduleController/View implementaciju u okviru
  ovog review nalaza bez novog implementerskog prolaza.
- Ne premještati drag-and-drop mutaciju u AppointmentController u F1 fixu;
  to je odvojeni postojeći arhitektonski dug.
- Ne mijenjati servisni sloj, dijaloge, backend, modele ili migracije.

## SLJEDEĆE

Codex test-quality review je PASS. Claude sada radi Reviewer 2 arhitektonski
pregled; Radovan human approval dolazi tek nakon oba PASS review-a.
