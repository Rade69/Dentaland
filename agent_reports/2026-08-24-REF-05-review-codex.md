# REF-05 — Codex independent review (test kvalitet)

```yaml
verdict: REJECT
scope: PASS
acceptance: FAIL
architecture: PASS
security: PASS
blocking_findings:
  - "F1: Query-counter test koristi samo _FakeView i ne hvata regresiju u stvarnim WeekView/DayView klasama; privremeno vraćen interni appointments_for_range poziv u WeekView.render_schedule, a svih 6 novih testova je i dalje prošlo."
```

## CILJ

Nezavisno provjeriti da REF-05 stvarno svodi scheduler refresh na jedan
snapshot, ne renderuje skriveni view, čuva usklađen doctor state i da izmjene
postojećih GUI testova nisu oslabile njihove invarijante.

## URAĐENO

- Potvrđeni grana `task/REF-05-schedule-controller`, commit `7692f31` i base
  `daf3074` kao ancestor.
- `pytest tests/ -q`: **347 passed**, 11 warnings.
- `ruff check src/dentaland desktop backend tests`: čist.
- `mypy src/dentaland desktop backend`: čist, 43 source fajla.
- Scope odgovara Task Contractu. Promijenjeni su samo novi ScheduleController,
  MainWindow, Day/Week view, tri pripadajuća postojeća test fajla, novi
  controller test i agent reports. Forbidden paths nisu dirani.

### F1 — blocking: glavni query test daje lažni PASS

`tests/test_gui/test_schedule_controller.py` instancira Controller isključivo
sa `_FakeView`. Taj fake samo sprema proslijeđeni dataset i nikad ne izvršava
stvarni `WeekView.render_schedule()` ili `DayView.render_schedule()`.

Adversarna mutacija:

1. U stvarni `WeekView.render_schedule()` privremeno je dodat direktan
   `store.appointments_for_range(...)`, čime se refresh vraća sa jednog na dva
   appointments fetcha za aktivni week view.
2. Pokrenut je `pytest tests/test_gui/test_schedule_controller.py -q`.
3. Stvarni rezultat: **6 passed in 0.07s**.
4. Mutacija je potpuno vraćena.

Zato test dokazuje samo da sam Controller jednom pozove fake store prije nego
što preda podatke fake view-u. Ne dokazuje glavnu acceptance tvrdnju da
stvarni integrisani refresh ostaje na jednom fetchu ako se view regresivno
vrati internom čitanju. Potreban je integracijski query-counter test sa pravim
`WeekView` i `DayView` (ili ekvivalentna provjera njihovog stvarnog
`render_schedule` puta) koji pada na ovoj mutaciji.

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

Crush treba dodati integracijski query-counter test sa stvarnim WeekView i
DayView koji pada kada bilo koji view ponovo interno pozove
`appointments_for_range`, zatim ponoviti puni verification paket. Nakon toga
Codex ponavlja samo F1 mutacionu provjeru. Claude review i Radovan human
approval čekaju Codex PASS.
