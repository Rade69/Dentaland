---
task_id: FIX-05
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: "Implementacija (Pi, commit 40eb79a) + review (Claude): PASS. Vidi agent_reports/2026-08-21-FIX-05-pi.md i .../2026-08-21-FIX-05-review-claude.md. MEDIUM risk — čeka human approval prije merge-a."
created_at: 2026-08-21
---

# FIX-05 — DayView drag & drop

## Task Contract

**Cilj:** `WeekView` podržava prevlačenje termina mišem da promijeni
vrijeme; `DayView` nema drag & drop uopšte — nedosljedan mentalni model
(Sedmica: prevuci termin i radi; Dan: ne radi ništa).

**Risk:** MEDIUM

**Izvor:** `docs/dentaland-desktop-korektivni-plan.md`, sekcija 6
(PRIORITET 6). Pun kontekst korektivnog plana (FIX-01 do FIX-06) tamo —
ovaj task pokriva SAMO FIX-05, ne šire.

## Obavezna arhitektonska odluka — VEĆ DONESENA, ne preispitivati

DayView kolone su **doktori** (za razliku od WeekView gdje su kolone
dani). To znači: prevlačenje unutar DayView-a između kolona bi značilo
promjenu doktora, ne promjenu vremena — potpuno drugačija operacija od
WeekView-ovog drag & drop-a (koji samo mijenja vrijeme/dan, doktor
ostaje isti, jer `store.move()` ne prima `doctor_id`).

Plan eksplicitno dozvoljava skraćenje obima upravo za ovaj slučaj: "u
prvoj iteraciji podržati drag samo unutar iste doctor kolone; između
doktora ostaviti 'Uredi termin'." **Ova odluka je već donesena za ovaj
kontrakt** — FIX-05 implementira SAMO drag unutar iste kolone (mijenja
vrijeme, doktor ostaje isti). Drag preko granice kolone (drugi doktor)
se **odbija** (drop se ignoriše, termin ostaje gdje je bio) — ne
implementirati promjenu doktora putem drag-a, to je eksplicitno van
obima ovog taska (za to postoji "Uredi termin").

## Root cause / referentna implementacija (već locirano) — WeekView

`desktop/views/week_view.py` ima kompletan, radni obrazac za kopiranje:

- **Linija 155**: `self.setDragDropMode(QTableWidget.DragDrop)` (uz
  postojeći `# type: ignore[attr-defined]` komentar za PySide6 stub gap
  — kopirati i taj komentar, isti razlog važi).
- **Linije 378–382**: appointment ćelije dobijaju
  `Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable |
  Qt.ItemFlag.ItemIsDragEnabled` (DayView trenutno NEMA
  `ItemIsDragEnabled` na svojim appointment ćelijama — `day_view.py`
  linije ~205-207, samo `ItemIsEnabled | ItemIsSelectable`).
- **Linija 332**: prazne ćelije dobijaju dodatni
  `Qt.ItemFlag.ItemIsDropEnabled` (DayView trenutno NEMA ovo na svojim
  praznim ćelijama — `day_view.py` linija ~169, samo
  `ItemIsEnabled | ItemIsSelectable`).
- **Linije 499–514**: `move_appointment_to_slot(appt_id, row, col) ->
  bool` — dohvati termin, provjeri da ciljna ćelija nije zauzeta DRUGIM
  terminom, izračunaj `new_start` iz `_slot_datetime`, sačuvaj trajanje,
  `store.move(appt_id, new_start, new_end)` unutar `try/except
  OverlapError: return False`, na uspjeh `refresh()` +
  `appointment_moved.emit(appt)` + `return True`.
- **Linije 518–526**: `mousePressEvent` override — na lijevi klik,
  zapamti koji je termin (ako ijedan) u ćeliji na poziciji klika kao
  `self._drag_appt_id`, prije poziva `super().mousePressEvent(event)`.
- **Linije 528–538**: `dropEvent` override — izračunaj red/kolonu iz
  pozicije drop-a, pozovi `move_appointment_to_slot`, `event.accept()`
  na uspjeh inače `event.ignore()`.
- **Linija 90**: `appointment_moved = Signal(object)` (trenutno
  nigdje ne slušan u `main_window.py` — ostaje tako, samo API simetrija
  sa WeekView, ne treba dodatno kablovanje).

## Šta uraditi u `day_view.py`

1. Dodati `appointment_moved = Signal(object)` uz postojeće signale.
2. `__init__`: dodati `self.setDragDropMode(QTableWidget.DragDrop)  #
   type: ignore[attr-defined]` i `self._drag_appt_id: int | None = None`.
3. U `refresh()`: dodati `Qt.ItemFlag.ItemIsDropEnabled` na prazne
   ćelije (inicijalni loop), i `Qt.ItemFlag.ItemIsDragEnabled` na
   appointment ćelije (grouped loop).
4. Dodati `move_appointment_to_slot(self, appt_id: int, row: int, col:
   int) -> bool`:
   - dohvati `appt = self.store.get(appt_id)`; `None` → `return False`.
   - **provjeri da je `col` ISTA kolona kao trenutni doktor termina**
     (`self._doctor_ids.index(appt.doctor_id) == col`, ili ekvivalentno
     `col < len(self._doctor_ids) and self._doctor_ids[col] ==
     appt.doctor_id`) — ako NIJE, `return False` (cross-doctor drag
     odbijen, po arhitektonskoj odluci gore).
   - provjeri da ciljna ćelija nije zauzeta DRUGIM terminom (isti
     obrazac kao WeekView, koristeći `self._appointments_by_cell()`).
   - `new_start = self._slot_datetime(row)` (BEZ `col` parametra —
     `DayView._slot_datetime` ima signature `(row, extra_minutes=0)`,
     različito od WeekView-ovog `(row, col, extra_minutes)` jer dan je
     fiksan na `self.day`), `new_end = new_start + (appt.end -
     appt.start)`.
   - `try: self.store.move(appt_id, new_start, new_end) except
     OverlapError: return False`.
   - na uspjeh: `self.refresh()`, `self.appointment_moved.emit(appt)`,
     `return True`.
5. Dodati `mousePressEvent(self, event: QMouseEvent) -> None` override
   — isti obrazac kao WeekView (zapamti `_drag_appt_id` iz
   `_appointments_by_cell()` na poziciji klika), pa
   `super().mousePressEvent(event)`. **Ne dirati `_pending_click_minutes`
   logiku** — DayView nema `_half_slot_minutes_at` (WeekView-specifična
   finija granularnost klika), i to nije u obimu ovog taska; ostaviti
   `_pending_click_minutes` kako jeste (ostaje 0, nepromijenjeno).
6. Dodati `dropEvent(self, event: QDropEvent) -> None` override — isti
   obrazac kao WeekView.
7. Novi importi: `QDropEvent`, `QMouseEvent` iz `PySide6.QtGui`;
   `OverlapError` iz `dentaland.services` (dopuniti postojeći
   `from dentaland.services import AppointmentDTO` import).

Ne duplirati/hakovati `store.move()` — ono već ispravno mijenja SAMO
vrijeme, ne doktora (potvrđeno u `booking.py`, nema `doctor_id`
parametra). Cross-doctor slučaj se namjerno odbija u
`move_appointment_to_slot`, ne u `store.move()`.

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
desktop/views/main_window.py
desktop/views/dialogs/**
```

## Obavezni regression testovi

Koristiti isti test-obrazac kao `tests/test_gui/test_week_view.py`
(`test_prevlacenje_termina_azurira_vrijeme`,
`test_drag_drop_odbija_pokrivenu_celiju`) — **pozivati
`move_appointment_to_slot(...)` direktno**, ne simulirati stvarne Qt
drag mouse evente (fragilno, WeekView testovi to namjerno izbjegavaju).

1. Prevlačenje unutar iste doktor-kolone ažurira vrijeme:
   ```text
   termin za Ljubu u 09:00
   move_appointment_to_slot(appt.id, <red za 11:00>, <Ljubina kolona>) → True
   store.get(appt.id).start == <11:00 istog dana>
   ```
2. Prevlačenje u ZAUZETU ćeliju (drugi termin) se odbija:
   ```text
   dva termina za Ljubu (09:00 i 11:00)
   move_appointment_to_slot(<09:00 termin>.id, <red za 11:00>, <Ljubina kolona>) → False
   oba termina zadržavaju originalno vrijeme
   ```
3. **Prevlačenje u DRUGU doktor-kolonu se odbija** (ključna
   arhitektonska odluka ovog taska):
   ```text
   termin za Ljubu u 09:00
   move_appointment_to_slot(appt.id, <isti red>, <Zorkina kolona>) → False
   store.get(appt.id).doctor_id nepromijenjen (i dalje Ljubo)
   store.get(appt.id).start nepromijenjen
   ```
4. Preklapanje sa DRUGIM terminom istog doktora (izvan trenutno
   prikazane ćelije, ali u istom vremenskom rasponu nakon pomjeranja)
   vraća `False` (`OverlapError` uhvaćen) — analogno WeekView pokrivanju
   `OverlapError` slučaja ako postoji u tom test fajlu, inače novi test.
5. Regresija — svi postojeći `test_day_view.py` testovi (klik na
   termin/prazan slot, blockout, izbriši akcija) i dalje prolaze
   nepromijenjeni.

## Acceptance criteria

- [ ] Prevlačenje termina unutar iste doktor-kolone u DayView mijenja
      vrijeme, isto kao u WeekView.
- [ ] Prevlačenje između doktor-kolona (drugi doktor) je odbijeno —
      termin ostaje nepromijenjen (ni vrijeme ni doktor).
- [ ] Prevlačenje u zauzetu ćeliju je odbijeno.
- [ ] Preklapanje (OverlapError) je uhvaćeno i odbija drop.
- [ ] Postojeći DayView klik/blockout/kontekst-meni funkcionalnost
      nije regresirana.
- [ ] Nema izmjena van `allowed_paths`, posebno `store.move()` u
      `booking.py` nije mijenjan.

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline za poređenje (izmjereno 21.8.2026 na `main` nakon `FIX-04`):
pytest 272 passed, ruff clean, mypy clean (0 issues, 35 fajlova).

## Review

Claude, nezavisan od implementera. MEDIUM risk — po tabeli u
`docs/dentaland-agentski-razvoj.md` human approval (Radovan) JE
obavezan prije merge-a.

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim` na
`desktop/views/day_view.py`. Radi u zasebnom git worktree
(`Dentaland-worktrees/FIX-05-<slug>`, grana `task/FIX-05-<slug>`).
