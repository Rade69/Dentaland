---
task_id: FIX-01
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: "MERGED → INTEGRATION_VERIFIED → DONE (merge 9808475). Human approval: Radovan. Post-merge gate na main: pytest 258 passed, ruff clean, mypy clean (0 issues, 35 fajlova)."
created_at: 2026-08-21
---

# FIX-01 — DayView mora prikazivati blockout/time-off

## Task Contract

**Cilj:** `WeekView` prikazuje blokade (`TimeOff`) i pauze/split-shift
kao neklikabilne blokove, ali `DayView` ih trenutno uopšte ne prikazuje
— učitava samo termine. To stvara opasnu nedosljednost: u Sedmici
doktor izgleda blokiran 10:00–12:00, u Danu isti termin izgleda
slobodan i može se zakazati.

**Risk:** MEDIUM

**Izvor:** `docs/dentaland-desktop-korektivni-plan.md`, sekcija 1
(PRIORITET 1). Pun kontekst korektivnog plana (FIX-01 do FIX-06) tamo —
ovaj task pokriva SAMO FIX-01, ne šire.

## Root cause (već lociran, ne treba ponovo istraživati)

`desktop/views/day_view.py`:

- linija 32: `_BLOCK_ROLE = Qt.ItemDataRole.UserRole + 1` je definisan
  ali **nikad korišten** — ostatak koda ga ne postavlja niti čita.
- `refresh()` (linije 160–207) samo iscrtava termine iz
  `_fetch_appointments()`; ne postoji ekvivalent WeekView-ovog
  `_fetch_blocks()`/`_block_cell_span()`/render-a blokova.
- `_on_cell_clicked()` (linije 256–261) emituje `slot_selected` čim
  ćelija nema termin — bez provjere da li je ćelija blokirana.

Poređenje — `desktop/views/week_view.py` već ima tačno ono što treba
kopirati/prilagoditi:

- `_fetch_blocks()` (linije 275–281): zove
  `store.time_off_for_week(week_start)` i `store.breaks_for_week(week_start)`
  ako postoje (`getattr(..., callable)` guard — servis možda nema oba).
- `_block_cell_span()` (linije 283–299): mapira jedan blok na
  `(row, col), span` unutar sedmičnog grida, klipuje na
  `DAY_START_HOUR`/`DAY_END_HOUR`.
- `refresh()` (linije 319–341): iscrtava blokove PRIJE termina, postavlja
  `block_item.setData(_BLOCK_ROLE, True)`.
- `_on_cell_clicked` ekvivalent (linija 430): `if item is not None and
  not item.data(_BLOCK_ROLE): self.slot_selected.emit(...)`.

**Bitna razlika WeekView vs DayView layout:** u WeekView koloni su dani
(pa `_block_cell_span` računa `col` iz datuma bloka), u DayView koloni
su **doktori** (`self._doctor_ids`), redovi su vremenski slotovi za
JEDAN dan (`self.day`). `time_off_for_week`/`breaks_for_week` primaju
`week_start: date`, ne pojedinačni dan — DayView mora sam izračunati
`week_start` iz `self.day` (isti obrazac kao
`main_window.py:75`: `today - timedelta(days=today.weekday())`) i
zatim filtrirati/klipovati blokove na `self.day`.

## Šta uraditi

1. Dodati `_fetch_blocks(self) -> list` u `DayView` — poziva
   `time_off_for_week`/`breaks_for_week` na `week_start` izračunat iz
   `self.day`, filtrira blokove čiji lokalni datum početka (`block.start
   .astimezone(SARAJEVO).date()`) odgovara `self.day` (ista pojednostavljena
   pretpostavka koju već koristi WeekView — ne graditi robusniju logiku
   za blokove koji prelaze granicu dana, to nije ni WeekView pravilo).
2. Dodati `_block_row_span(self, block) -> tuple[int, int] | None` —
   analogno `WeekView._block_cell_span`, ali vraća samo `(row, span)`
   jer je kolona određena doktorom (`self._doctor_ids.index(block.doctor_id)`,
   preskočiti blok ako doktor nije među trenutnim kolonama — isti guard
   kao za termine na liniji 121).
3. U `refresh()`: iscrtati blokove PRIJE grupisanja termina (isti
   redoslijed kao WeekView — blok prvo, pa termini), sa `setSpan` kad je
   span > 1, `block_item.setData(_BLOCK_ROLE, True)`,
   `Qt.ItemFlag.ItemIsEnabled` (bez `ItemIsSelectable`, isto kao
   WeekView), vizuelno konzistentno sa WeekView-ovim block card stilom
   (`background:#f1f3f5; color:#1f2937; border:1px solid #cfd6dd;
   border-radius:7px; margin:5px 9px; padding:5px; font-weight:600;`).
4. U `_on_cell_clicked()`: prije `slot_selected.emit(...)`, provjeriti
   `item.data(_BLOCK_ROLE)` — ako je blok, ne emitovati ništa (isto
   ponašanje kao WeekView).
5. Novi importi potrebni: `timedelta` (iz `datetime`, već se uvozi
   `date, datetime`) i `math` (za `math.ceil`, isto kao week_view.py).

Ne duplirati business logiku — `time_off_for_week`/`breaks_for_week` iz
`src/dentaland/services/booking.py` se NE mijenjaju i NE diraju.
`CalendarBlockDTO` se ne mijenja. Ako se tokom rada pokaže da postojeći
servisni helperi stvarno nisu dovoljni (malo vjerovatno — WeekView ih
već koristi identično), ne mijenjati `booking.py` bez prethodnog
`OUT_OF_SCOPE_FINDING` i odobrenja — nije predviđeno ovim kontraktom.

## Allowed paths

```text
desktop/views/day_view.py
tests/test_gui/test_day_view.py
```

## Forbidden paths

```text
src/dentaland/models.py
migrations/
src/dentaland/services/booking.py
desktop/views/week_view.py
desktop/views/dialogs/**
desktop/views/main_window.py
```

## Obavezni regression testovi

Koristiti pravi `appointment_service` fixture (isti obrazac kao
postojeći `tests/test_gui/test_day_view.py`) i njegov stvaran
`create_time_off(doctor_id, start, end, reason=...)` — ne mock, WeekView
testovi za blockout koriste `SimpleNamespace`/`FakeStore` jer taj view
ima drugačiji fixture obrazac, ali `test_day_view.py` već konzistentno
koristi pravi servis.

1. Blockout je vidljiv u DayView:
   ```text
   appointment_service.create_time_off(doctor_id=<Zorka>, start=DAY 10:00, end=DAY 12:00, reason="Godišnji")
   view = DayView(appointment_service, DAY)
   view.item(<red za 10:00>, <Zorkina kolona>).text() == "Godišnji"
   ```
2. Blokiran slot ne emituje `slot_selected`:
   ```text
   isti blockout kao gore
   view.slot_selected.connect(emitted.append)
   view.cellClicked.emit(<red za 10:00>, <Zorkina kolona>)
   emitted == []
   ```
3. Pauza (split-shift, `breaks_for_week`) je vidljiva ako je već
   podržana test-podacima za `appointment_service` fixture (provjeriti
   da li fixture ima split-shift `WorkingHours`; ako nema, dovoljno je
   pokriti samo TimeOff slučaj + eksplicitno napisati u agent_report da
   pauza nije bila testabilna sa postojećim fixture-om — ne izmišljati
   nove fixture podatke van `allowed_paths`).
4. Regresija — termin i dalje ispravno renderuje kad NEMA blokade
   (postojeći `test_day_view_prikazuje_termin_u_koloni_doktora` ne smije
   se pokvariti).
5. Regresija — klik na prazan, NEBLOKIRAN slot i dalje emituje
   `slot_selected` (postojeći test ne smije regresirati).

## Acceptance criteria

- [ ] Blockout (`TimeOff`) vidljiv u DayView, vizuelno konzistentan sa
      WeekView.
- [ ] Pauza/split-shift vidljiva u DayView ako je testabilna.
- [ ] Blokiran slot se ne može kliknuti kao slobodan (`slot_selected` se
      ne emituje).
- [ ] Appointment rendering i klik na prazan slot nisu regresirani.
- [ ] Nema izmjena van `allowed_paths`, posebno nema izmjena u
      `booking.py`/`week_view.py`.

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline za poređenje (izmjereno 21.8.2026 na `main` nakon `FIX-02`):
pytest 256 passed, ruff clean, mypy clean (0 issues, 35 fajlova). Novi
testovi treba da povećaju taj broj, ne smanje ga; ruff i mypy moraju
ostati čisti.

## Review

Claude, nezavisan od implementera. MEDIUM risk — po tabeli u
`docs/dentaland-agentski-razvoj.md` human approval (Radovan) JE
obavezan prije merge-a.

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim` na
`desktop/views/day_view.py`. Radi u zasebnom git worktree
(`Dentaland-worktrees/FIX-01-<slug>`, grana `task/FIX-01-<slug>`).
