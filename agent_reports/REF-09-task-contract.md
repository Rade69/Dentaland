---
task_id: REF-09
risk: LOW
implementer: pi
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit 115e86f, 2026-08-26), post-merge integration gate PASS (357 pytest, ruff, mypy)."
review_summary: >-
  Codex runda 1: REJECT (F1 - GUI testovi provjeravali samo krajnje
  stanje, ne PUT kroz Controller; adversarno dokazano lazan PASS na
  starom direktnom pozivu). Implementer dodao dva runtime testa koja
  monkeypatch-uju Controller i postavljaju direktne store metode da
  bacaju ako se pozovu mimo njega. Codex runda 2: PASS (sam ponovio
  adversarnu mutaciju). Claude: PASS_WITH_NOTES - arhitektura cista,
  dosljedna REF-07 self-contained Controller obrascu; jedna non-blocking
  napomena o implicitnom scope-u privatne Controller instance (nema
  MainWindow doctor state, bezopasno za trenutnu upotrebu).
created_at: 2026-08-25
merged_at: 2026-08-26
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

**Obrazac: `DashboardPanels` konstruiše SVOJU privatnu `AppointmentController`
instancu**, analogno već postojećem `self._request_controller =
RequestController(store)` u istom fajlu (`requests_panel.py:29`) — koji je
sam sebi dovoljan, ne dijeli instancu sa `main_window.py`.
`RequestController` je već dokazano instanciran NEZAVISNO na dva mjesta
(`requests_panel.py` i `requests_page.py`) — isti obrazac se ovdje ponavlja.
Ovo NAMJERNO izbjegava dijeljenje `MainWindow`-ove `self._controller`
instance, jer bi to zahtijevalo izmjenu `main_window.py` (dodatna
`allowed_paths` stavka koja bi se preklapala sa REF-10/11/12/14 i blokirala
paralelni rad — vidi `.agent/CURRENT_STATE.md` sekciju o REF-09..14 planu).

1. **`AppointmentController.handle_appointment_action`**
   (`appointment_controller.py:180-186`, `method_map`): dodati novi ključ
   `"reject"` → `"cancel"`, analogno postojećem `"confirm"` →
   `"mark_confirmed"` (isti bezdijaloški obrazac — direktan poziv store
   metode, `except ValueError` → `QMessageBox.warning`, pa
   `self._refresh_callback()`). Postojeći `"cancel"` ključ (linija 170-174,
   dijalog-bazirani flow) ostaje netaknut — `"reject"` je NOVI, odvojen
   ključ, ne zamjena.
2. **`requests_panel.py`**: `DashboardPanels.__init__` dodaje
   ```python
   self._appointment_controller = AppointmentController(store, self, self._on_appointment_changed)
   ```
   (novi import `from desktop.controllers.appointment_controller import
   AppointmentController`). `_on_appointment_changed` je nova mala helper
   metoda koja radi tačno ono što `_confirm_scheduled`/`_cancel_scheduled`
   ranije radili nakon mutacije: `self.refresh(); self.changed.emit()`.
   `_confirm_scheduled`/`_cancel_scheduled` postaju:
   ```python
   def _confirm_scheduled(self, appt_id: int) -> None:
       self._appointment_controller.handle_appointment_action(appt_id, "confirm")

   def _cancel_scheduled(self, appt_id: int) -> None:
       self._appointment_controller.handle_appointment_action(appt_id, "reject")
   ```
   `AppointmentController`-ov `_parent_widget` je ovdje `DashboardPanels`
   instanca (ne `MainWindow`) — to je bezopasno za ova dva action-a, jer
   `method_map` grana (`confirm`/`reject`) ne čita `_doctors`/
   `_has_doctors`/`_current_doctor_id` (te getattr pozive koristi samo
   `on_slot_selected`/`edit_appointment`, koji se odavde ne pozivaju).

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
agent_reports/**
```

**`main_window.py` je NAMJERNO van scope-a** — vidi obrazloženje gore.

## Forbidden paths

```text
desktop/views/main_window.py
desktop/views/day_view.py
desktop/views/week_view.py
desktop/views/blockout_panel.py
desktop/views/settings_panel.py
desktop/controllers/schedule_controller.py
desktop/controllers/request_controller.py
desktop/controllers/print_controller.py
desktop/controllers/blockout_controller.py
desktop/controllers/settings_controller.py
src/dentaland/services/**
models.py
migrations/**
backend/**
```

(F1/F2/F3 su odvojeni budući taskovi — REF-10/11/12 — ne dirati te
fajlove ovdje. Nulto preklapanje sa REF-11/REF-12/REF-13 je namjerno —
omogućava paralelan rad, vidi plan u razgovoru sa Radovanom 25.8.2026.)

## Review

Codex (test kvalitet/adversarial) pa Claude (arhitektura), po REF paket
konvenciji. Human approval (Radovan) prije merge-a.

## Napomena za implementera

Ovo je MEHANIČKO ožičavanje postojeće, već testirane Controller logike —
ne pisati novu poslovnu logiku. Ako se otkrije da `_refresh_dashboard`
NE pokriva sve što `changed.emit()` ranije radio (npr. neki drugi widget
sluša `dashboard_panels.changed` signal osim `main_window.py`), prijaviti
kao `OUT_OF_SCOPE_FINDING` prije nego što se scope taska proširi.
