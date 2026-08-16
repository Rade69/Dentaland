# Plan — DENT-002 (MEDIUM)

## Cilj
PySide6 desktop GUI ljuska (Faza 0): sedmični pregled, klik-za-unos, prevlačenje,
napomena kao slobodan tekst, dugme za štampu (stub) — sve nad in-memory fake
dataclass slojem, bez SQLAlchemy.

## Pogođeno
- Novi paket `desktop/` (fake_data.py, app.py, views/week_view.py,
  views/appointment_dialog.py, views/main_window.py).
- Novi testovi `tests/test_gui/` (conftest + tri test fajla).

## Plan
1. `desktop/fake_data.py` — `@dataclass Appointment` + `FakeStore` (in-memory),
   IANA zona `Europe/Sarajevo` (aware datetime, nikad naivni).
2. `desktop/views/week_view.py` — QTableWidget: 7 kolona × 30-min slotovi
   (08:00–18:00); klik na prazan slot emituje `slot_selected`; drag & drop
   zauzetog slota poziva `move_appointment_to_slot`.
3. `desktop/views/appointment_dialog.py` — ime/telefon/email/usluga/napomena,
   bez validacije.
4. `desktop/views/main_window.py` — WeekView kao central widget, "Štampaj
   raspored" akcija (TODO stub), povezivanje slota na dijalog → store.
5. `desktop/app.py` — ulazna tačka + `FakeStore.seeded()` za prvi prikaz.

## Šta NE dirati
`pyproject.toml`, `src/dentaland/**`, `migrations/**`, `docs/**`, `CLAUDE.md`,
`AGENTS.md`. Sve izmjene isključivo u `desktop/**` i `tests/test_gui/**`.

## Plan verifikacije
- `pytest tests/test_gui` (offscreen QPA platforma).
- `ruff check desktop tests/test_gui`.
- `grep -r sqlalchemy desktop/views` → očekivano prazan rezultat.

## Rollback
Sve je novi kod na grani `task/DENT-002-gui-shell`; ništa postojeće se ne mijenja.
Poništiti: `git restore`/brisanje novih fajlova prije ikakvog commit-a.

## Odbačene opcije
- Dnevni prikaz — Task Contract traži sedmični kao početni ekran.
- QTableView + QAbstractTableModel — QTableWidget je dovoljan za ljusku,
  manje indirekcije, bez gubitka testabilnosti.
- Validacija polja — namjerno izostavljena (slobodna forma sveske).
