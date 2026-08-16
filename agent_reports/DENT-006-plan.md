# Plan — DENT-006 (MEDIUM)

## Cilj
Redizajn sedmičnog rasporeda: termini sva tri doktora istovremeno, boja po
doktoru; filter tabovi "Svi doktori"/"Dr Ljubo"/"Dr Zorka"/"Dr Ana"; unos
termine traži doktora kad je "Svi doktori" aktivan; drag&drop bez regresije.

## Pogođeno
- `src/dentaland/services/booking.py` — `all_combined()`, DTO nosi
  `doctor_id`/`doctor_name`, `move()` nezavisan od `self.doctor_id`.
- `desktop/views/week_view.py` — kombinovani prikaz, boje, `set_filter`.
- `desktop/views/main_window.py` — tabovi umjesto dropdown-a, izbor doktora
  pri unosu (QInputDialog).
- Testovi: `tests/test_services.py`, `tests/test_gui/` (+ novi fajl).

## Plan
1. `AppointmentDTO` + `doctor_id`/`doctor_name`; `_to_dto` ih popunjava.
2. `AppointmentService.all_combined()` — svi termini, sort po start_time.
3. `move()` — koristi `appt.doctor_id` (ne `self.doctor_id`) da drag&drop
   radi za bilo kojeg doktora u kombinovanom prikazu.
4. `doctors()` sortira po `id` (redoslijed tabova Ljubo/Zorka/Ana, ne
   alfabetski Ana/Ljubo/Zorka).
5. `WeekView`: `_fetch_appointments` (all_combined ako postoji, inače all),
   boje iz `store.doctors()` (paleta), `set_filter(doctor_id|None)`,
   ćelija = lista termina (više doktora može dijeliti slot).
6. `MainWindow`: QTabBar filter + QVBoxLayout (tabovi iznad rasporeda);
   `_on_slot_selected` bira doktora (QInputDialog) kad je "Svi doktori".
7. Drop na zauzet slot prepušten servisu (OverlapError) — dozvoljava termin
   drugog doktora na istom slotu.

## Šta NE dirati
`models.py`, `migrations/`, `services/requests.py`, `backend/`, `web/`,
`desktop/fake_data.py`, `desktop/views/appointment_dialog.py`, `CLAUDE.md`,
`AGENTS.md`, `docs/**`.

## Plan verifikacije
- `pytest tests/ -q`
- `ruff check src/dentaland desktop tests`
- `grep -ri sqlalchemy desktop/views/*.py` → očekivano prazno

## Rollback
Izmjene na grani `task/DENT-006-raspored-svi-doktori`; fake_data.py i
appointment_dialog.py netaknuti (kompatibilnost sa FakeStore testovima
očuvana kroz `getattr`). Nema commit-a bez naloga.

## Odbačene opcije
- Dropdown (QComboBox) — Task Contract traži tabove.
- Sidebar / paneli iz mokapa — eksplicitno van obima.
- Custom QTableView delegate za preklapajuće blokove — previše za ovaj obim;
  QTableWidgetItem + lista termina po ćeliji + boja doktora je dovoljno.
