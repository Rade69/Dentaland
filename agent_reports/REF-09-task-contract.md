---
task_id: REF-09
risk: LOW
implementer: TBD
reviewers: [codex, claude]
status: "OPEN — task contract napisan prije koda"
created_at: 2026-08-25
---

# REF-09 — Dashboard "Čekaju potvrdu" akcije kroz AppointmentController (F4)

## Kontekst

`agent_reports/2026-08-25-REF-FINAL-acceptance-review-codex.md` i
`agent_reports/2026-08-25-REF-FINAL-acceptance-review-claude.md` (finalni
paketni acceptance audit REF-00..08, oba nezavisno potvrdila) identifikuju
nalaz **F4**: `desktop/views/requests_panel.py` (`DashboardPanels`) poziva
`self.store.mark_confirmed(appt_id)` i `self.store.cancel(appt_id)`
**direktno**, mimoilazeći `AppointmentController` — iako
`AppointmentController.handle_appointment_action` VEĆ ispravno implementira
identičnu poslovnu logiku za scheduler (day/week view).

Radovanova eksplicitna odluka (25.8.2026): nema "dokumentovanog duga za
kasnije" u ovom projektu — svaki nalaz iz finalnog audita odmah postaje
task. REF-09 je prvi i najjeftiniji od četiri (F1-F4), jer
`AppointmentController` već postoji — ovaj task ga samo ožičava na
dashboard, ne piše nov Controller.

## Cilj

`DashboardPanels._confirm_scheduled`/`_cancel_scheduled`
(`requests_panel.py:143-151`) prestaju pozivati `self.store.*` direktno —
idu isključivo kroz postojeći `AppointmentController`.

**Ključno ograničenje: ponašanje se NE smije promijeniti.** Trenutno
dashboard "Potvrdi"/"Odbaci" dugmad rade BEZ potvrdnog dijaloga (za razliku
od scheduler-ovog cancel flow-a koji otvara `CancelAppointmentDialog`).
`AppointmentController.cancel_appointment(appt)` (linija 214-227) UVIJEK
otvara taj dijalog — ne smije se koristiti direktno za dashboard "Odbaci",
jer bi to bila tiha promjena UX-a (novi dijalog gdje ga ranije nije bilo),
što je van scope-a ovog taska.

## Traženo rješenje (konkretan oblik, ne prepušteno implementeru da nagađa)

1. **`AppointmentController.handle_appointment_action`**
   (`appointment_controller.py:180-186`, `method_map`): dodati novi ključ
   `"reject"` → `"cancel"`, analogno postojećem `"confirm"` →
   `"mark_confirmed"` (isti bezdijaloški obrazac — direktan poziv store
   metode, `except ValueError` → `QMessageBox.warning`, pa
   `self._refresh_callback()`). Postojeći `"cancel"` ključ (linija 170-174,
   dijalog-bazirani flow) ostaje netaknut — `"reject"` je NOVI, odvojen
   ključ, ne zamjena.
2. **`main_window.py`**: proslijediti postojeću `self._controller`
   (`AppointmentController` instancu, već konstruisanu na liniji 116, PRIJE
   `self.dashboard_panels = DashboardPanels(...)` na liniji 141) u
   `DashboardPanels` konstruktor — ne praviti novu, drugu instancu
   Controllera.
3. **`requests_panel.py`**: `DashboardPanels.__init__` prima novi parametar
   (npr. `appointment_controller: AppointmentController`), čuva ga kao
   `self._appointment_controller`. `_confirm_scheduled`/`_cancel_scheduled`
   postaju:
   ```python
   def _confirm_scheduled(self, appt_id: int) -> None:
       self._appointment_controller.handle_appointment_action(appt_id, "confirm")

   def _cancel_scheduled(self, appt_id: int) -> None:
       self._appointment_controller.handle_appointment_action(appt_id, "reject")
   ```
   Ručni `self.refresh()`/`self.changed.emit()` pozivi u ove dvije metode
   se UKLANJAJU — `AppointmentController`-ov `refresh_callback` je već
   `MainWindow._refresh_dashboard`, koji već zove
   `self.dashboard_panels.refresh()` (linija 384). Provjeriti da
   `_refresh_dashboard` pokriva sve što je `changed.emit()` ranije
   trigerovalo (npr. `requests_page.refresh()`, badge brojevi) — ako ne
   pokriva sve, zadržati `self.changed.emit()` i samo ukloniti
   `self.refresh()` (izbjeći duplo osvježavanje, ne izgubiti postojeće).

## Acceptance

- [ ] `requests_panel.py` više ne sadrži `self.store.mark_confirmed`/
      `self.store.cancel` pozive;
- [ ] `grep -rn "self\.store\." desktop/views/requests_panel.py` daje 0
      mutacijskih poziva (samo `_call()` za read-only `pending_requests`/
      `awaiting_confirmation`/`cancelled_today` ostaju, to su read-ovi,
      ne mutacije — van scope-a ovog nalaza);
- [ ] postojeći GUI testovi za dashboard potvrdu/odbacivanje i dalje
      prolaze BEZ izmjene testa da traži dijalog (ponašanje bez dijaloga
      ostaje identično);
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti.

## Allowed paths

```text
desktop/controllers/appointment_controller.py
desktop/views/requests_panel.py
desktop/views/main_window.py
agent_reports/**
```

## Forbidden paths

```text
desktop/views/day_view.py
desktop/views/week_view.py
desktop/views/blockout_panel.py
desktop/views/settings_panel.py
desktop/controllers/schedule_controller.py
desktop/controllers/request_controller.py
desktop/controllers/print_controller.py
src/dentaland/services/**
models.py
migrations/**
backend/**
```

(F1/F2/F3 su odvojeni budući taskovi — REF-10/11/12 — ne dirati te
fajlove ovdje, izbjeći preklapanje scope-a i coordination.py claim-ova.)

## Review

Codex (test kvalitet/adversarial) pa Claude (arhitektura), po REF paket
konvenciji. Human approval (Radovan) prije merge-a.

## Napomena za implementera

Ovo je MEHANIČKO ožičavanje postojeće, već testirane Controller logike —
ne pisati novu poslovnu logiku. Ako se otkrije da `_refresh_dashboard`
NE pokriva sve što `changed.emit()` ranije radio (npr. neki drugi widget
sluša `dashboard_panels.changed` signal osim `main_window.py`), prijaviti
kao `OUT_OF_SCOPE_FINDING` prije nego što se scope taska proširi.
