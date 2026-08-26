---
task_id: REF-10
risk: MEDIUM
implementer: TBD
reviewers: [codex, claude]
status: "OPEN — task contract napisan prije koda"
created_at: 2026-08-26
---

# REF-10 — Scheduler drag&drop kroz AppointmentController (F1)

## Kontekst

Finalni acceptance audit REF-00..08
(`agent_reports/2026-08-25-REF-FINAL-acceptance-review-codex.md` +
`-claude.md`, oba nezavisno potvrdila) nalaz **F1**:
`desktop/views/day_view.py:349-367` i `desktop/views/week_view.py:464-478`
(`move_appointment_to_slot`) pozivaju `self.store.move(...)` **direktno**,
mimoilazeći `AppointmentController` — jedini od F1-F4 nalaza koji uključuje
scheduler drag&drop, ne dashboard/blockout/settings panel.

Radovanova odluka (25.8.2026): nema prihvaćenog duga, svaki nalaz odmah
postaje task. REF-09 (F4) i REF-11 (F2) su već DONE (merge `115e86f`,
`a87d423`) — ovo je treći.

**Risk je MEDIUM, ne LOW kao REF-09/11/12/13** — za razliku od tih taskova
(dashboard/blockout su čisto ožičavanje ili nov facade), ovdje se dira
`dropEvent`-om pokretana sinhrona logika sa `bool` povratnom vrijednošću
koja direktno kontroliše Qt drag&drop accept/ignore ponašanje — veći
prostor za suptilnu regresiju u interaktivnom UI ponašanju koje je teže
pokriti testom nego čist store poziv.

## Trenutno stanje (tačno, provjereno 26.8.2026)

`day_view.py:349-367`:

```python
def move_appointment_to_slot(self, appt_id: int, row: int, col: int) -> bool:
    appt = self.store.get(appt_id)
    if appt is None:
        return False
    if col < 0 or col >= len(self._doctor_ids) or self._doctor_ids[col] != appt.doctor_id:
        return False
    occupied = self._appointments_by_cell().get((row, col), [])
    if any(a.id != appt_id for a in occupied):
        return False
    new_start = self._slot_datetime(row)
    new_end = new_start + (appt.end - appt.start)
    try:
        self.store.move(appt_id, new_start, new_end)
    except OverlapError:
        return False
    self.appointment_moved.emit(appt)
    return True
```

`week_view.py:464-478` je strukturno identično (bez doctor-kolona provjere,
`_slot_datetime(row, col)` umjesto `_slot_datetime(row)`).

Ova metoda se poziva SAMO iz `dropEvent` (`day_view.py:383`,
`week_view.py:498`) — `bool` povratna vrijednost direktno određuje
`event.accept()`/`event.ignore()`. **Na `OverlapError` trenutno NEMA
dijaloga/poruke** — drop se tiho odbija (Qt vraća item vizuelno na staro
mjesto). Ovo ponašanje se NE SMIJE promijeniti — ne dodavati
`QMessageBox`/dijalog na neuspjeh, to bi bila tiha UX promjena van scope-a.

## Traženo rješenje (konkretan oblik)

**1. `AppointmentController`** (`appointment_controller.py`) — nova metoda,
čista (bez dijaloga, za razliku od ostalih metoda u ovoj klasi):

```python
def move_appointment_slot(self, appt_id: int, new_start: datetime, new_end: datetime) -> bool:
    try:
        self._store.move(appt_id, new_start, new_end)
    except OverlapError:
        return False
    return True
```

**2. `DayView.__init__` / `WeekView.__init__`** — svaka konstruiše svoju
privatnu `AppointmentController` instancu (isti self-contained obrazac kao
REF-09/11):

```python
self._appointment_controller = AppointmentController(store, self, lambda: None)
```

`refresh_callback=lambda: None` je NAMJERNO no-op — refresh nakon uspješnog
pomjeranja i dalje ide kroz POSTOJEĆI `appointment_moved` signal
(`self.appointment_moved.emit(appt)`, ostaje u View-u NETAKNUTO) →
`main_window.py`-ovu postojeću konekciju
(`week_view.appointment_moved.connect(lambda _appt: self._schedule_controller.refresh())`,
linije 130-135) — ta konekcija se NE DIRA. Controller ovdje služi
isključivo da premjesti `store.move()`+`OverlapError` logiku iz View-a, ne
da preuzme refresh orkestraciju (koja već ispravno postoji).

**3. `move_appointment_to_slot`** u oba fajla — zamijeniti SAMO
`try:`/`except OverlapError:` blok:

```python
if not self._appointment_controller.move_appointment_slot(appt_id, new_start, new_end):
    return False
```

Sve ostalo (occupancy provjere, doctor-kolona provjera u day_view,
`self.appointment_moved.emit(appt)`, `return True`) ostaje NETAKNUTO.

**4. Import cleanup:** `OverlapError` import (`day_view.py:32`,
`week_view.py:31`, oba dio `from dentaland.services import AppointmentDTO,
OverlapError`) postaje neiskorišten nakon ove izmjene — ukloniti `OverlapError`
iz tog import-a (zadržati `AppointmentDTO`), inače `ruff` puca na
unused-import.

**Zašto NE main_window.py:** za razliku od REF-04/05 gdje su View-Controller
konekcije ožičene u `main_window.py`, ovdje je self-contained
per-view-instanca obrazac (REF-09/11 presedan) namjerno izabran da se
izbjegne `main_window.py` i omogući paralelan rad sa REF-12/13. Postojeća
`appointment_moved` signal konekcija u `main_window.py` (linije 130-135)
ostaje potpuno netaknuta — ne treba je dirati.

## Acceptance

- [ ] `day_view.py`/`week_view.py` više ne sadrže `self.store.move(...)`
      pozive;
- [ ] `grep -n "self\.store\.move" desktop/views/day_view.py
      desktop/views/week_view.py` → 0 pogodaka;
- [ ] ponašanje na `OverlapError` ostaje identično (tih `event.ignore()`,
      bez dijaloga) — provjeriti eksplicitnim testom, ne pretpostaviti;
- [ ] `main_window.py` NIJE diran (provjeriti `git diff --stat`);
- [ ] postojeći GUI testovi za drag&drop (`test_day_view.py`,
      `test_week_view.py`, traži `move_appointment_to_slot`) i dalje
      prolaze;
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti.

## Upozorenje o test kvalitetu (unaprijed, iz REF-09/11 iskustva)

REF-09 i REF-11 su OBA prošla kroz Codex REJECT rundu jer su postojeći
testovi provjeravali samo krajnje stanje (store zapis), ne PUT (da li je
pozvan Controller). Isto pitanje će se postaviti i ovdje. Preporučeno:
odmah dodati test koji monkeypatch-uje `self._appointment_controller` (ili
postavlja `store.move` da baci `AssertionError` ako je pozvan direktno) i
potvrđuje da `move_appointment_to_slot` ide kroz Controller — ne čekati
Codexov nalaz da bi se to uradilo, ušteda jedne runde review-a.

## Allowed paths

```text
desktop/controllers/appointment_controller.py
desktop/views/day_view.py
desktop/views/week_view.py
agent_reports/**
```

## Forbidden paths

```text
desktop/views/main_window.py
desktop/views/requests_panel.py
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

Nulto preklapanje sa REF-12/REF-13 je namjerno — omogućava paralelan rad.

## Review

Codex pa Claude, human approval prije merge-a. Zbog MEDIUM rizika
(interaktivan drag&drop UI put), Codex review treba posebno provjeriti
`dropEvent` ponašanje kroz stvaran Qt test, ne samo pozivanje metode
direktno.

## Koordinacija

Namijenjen za paralelan rad uz REF-12 i/ili REF-13 — nema zajedničkih
`allowed_paths` sa njima, provjereno prije pisanja ovog kontrakta. Ne
preklapa se sa REF-09/REF-11 (već mergovani, `appointment_controller.py`
je sad zajednička ali stabilna osnova).
