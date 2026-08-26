---
task_id: REF-14
risk: MEDIUM
implementer: TBD
reviewers: [codex, claude]
status: "OPEN — task contract napisan prije koda"
created_at: 2026-08-26
---

# REF-14 — Doctor-state provideri umjesto getattr-fishing na parent widget-u

## Kontekst

Dokumentovan dug od REF-04/REF-05 (`.agent/CURRENT_STATE.md`, prije
26.8.2026 revizije): `AppointmentController` čita doctor-state (`_doctors`,
`_has_doctors`, `_current_doctor_id`) preko `getattr(self._parent_widget,
"<ime>", <default>)` — stringly-typed "pogađanje" imena privatnih atributa
na bilo kom objektu koji se desi da je `parent_widget`. Ranije opisano kao
"3-lokacijski state sync" (MainWindow + AppointmentController +
ScheduleController drže "isti" podatak).

**Ponovo istraženo 26.8.2026, prije pisanja ovog kontrakta — nalaz je
PRECIZNIJI nego ranija napomena:**

`ScheduleController._current_doctor_id` (`schedule_controller.py:56,140`)
je **mrtav kod** — postavlja se u `set_doctor_filter()`, ali se NIGDJE u
klasi (ni u testovima) ne čita. Stvaran filter rad radi
`self._week_view.set_filter(doctor_id)`, ne ovo polje. Dakle problem NIJE
"3 mjesta drže isti podatak" nego: **1 stvaran izvor istine
(`MainWindow`) + 1 stringly-typed čitalac (`AppointmentController`) + 1
potpuno mrtvo, neiskorišteno polje (`ScheduleController`)**.

REF-07-ov `week_start_provider: Callable[[], date]` obrazac (`PrintController`)
je već dokazan kao čistiji model za isti problem — eksplicitan, tipiziran
callable umjesto `getattr` pogađanja.

## Cilj

**1. Ukloniti mrtvo polje** — `schedule_controller.py`: obrisati
`self._current_doctor_id: int | None = None` (linija 56) i
`self._current_doctor_id = doctor_id` (linija 140, unutar
`set_doctor_filter`). `set_doctor_filter` i dalje radi identično (poziva
`self._week_view.set_filter(doctor_id)` + `self.refresh()`) — ovo je
čisto uklanjanje neiskorištenog stanja, ne promjena ponašanja.

**2. Zamijeniti getattr-fishing eksplicitnim provider callable-ovima** —
`appointment_controller.py`, konstruktor dobija tri OPCIONA keyword-only
parametra sa safe default-ima (identičnim ponašanju trenutnog getattr
fallback-a):

```python
def __init__(
    self,
    store: Any,
    parent_widget: QWidget,
    refresh_callback: Callable[[], None],
    *,
    doctors_provider: Callable[[], list] = lambda: [],
    has_doctors_provider: Callable[[], bool] = lambda: False,
    current_doctor_id_provider: Callable[[], int | None] = lambda: None,
) -> None:
    ...
    self._doctors_provider = doctors_provider
    self._has_doctors_provider = has_doctors_provider
    self._current_doctor_id_provider = current_doctor_id_provider

def _doctors(self) -> list:
    return self._doctors_provider()

def _has_doctors(self) -> bool:
    return self._has_doctors_provider()

def _current_doctor_id(self) -> int | None:
    return self._current_doctor_id_provider()
```

**Zašto opciono sa default-ima, ne obavezno:** tri od četiri postojeća
mjesta konstrukcije (`day_view.py:61`, `week_view.py:86`,
`requests_panel.py:31`, sve iz REF-09/REF-10) NIKAD ne pozivaju
`on_slot_selected`/`edit_appointment` (jedine metode koje čitaju doctor
state) — ne smiju biti prisiljene da prosljeđuju providere koje im ne
trebaju. Default lambda-e vraćaju TAČNO ono što bi `getattr(..., default)`
vratio danas — ponašanje ostaje identično za ta tri mjesta, BEZ izmjene
njihovog poziva.

**3. `main_window.py`** — jedino mjesto koje STVARNO treba doctor state,
prosljeđuje providere eksplicitno:

```python
self._controller = AppointmentController(
    store,
    self,
    self._refresh_dashboard,
    doctors_provider=lambda: self._doctors,
    has_doctors_provider=lambda: self._has_doctors,
    current_doctor_id_provider=lambda: self._current_doctor_id,
)
```

(Zamjenjuje trenutni jednostavan poziv `AppointmentController(store, self,
self._refresh_dashboard)` na liniji 116.)

**Šta OVO NE mijenja:** `_parent_widget` (weakref, REF-10) OSTAJE —
i dalje je potreban za Qt dialog/`QMessageBox` parenting
(`parent=self._parent_widget`). Ovaj task uklanja SAMO doctor-state
getattr čitanje preko njega, ne cijeli koncept parent widget-a.

## Acceptance

- [ ] `schedule_controller.py` više ne sadrži `_current_doctor_id` polje
      (ni deklaraciju ni assignment) — `set_doctor_filter` i dalje radi
      identično;
- [ ] `appointment_controller.py` čita doctor-state isključivo preko
      provider callable-ova, ne preko `getattr(self._parent_widget, ...)`;
- [ ] `main_window.py` eksplicitno prosljeđuje sva tri providera pri
      konstrukciji `self._controller`;
- [ ] `day_view.py`/`week_view.py`/`requests_panel.py` OSTAJU NETAKNUTI —
      njihova konstrukcija `AppointmentController(store, self, lambda: None)`
      i dalje radi bez izmjene (default provideri pokrivaju);
- [ ] postojeći GUI testovi (`test_main_window.py`,
      `test_appointment_controller.py`, `test_schedule_controller.py`) i
      dalje prolaze BEZ izmjene ponašanja — doctor izbor u scheduleru i
      dalje radi identično;
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti;
- [ ] `python scripts/agent_sensors.py --all` i dalje 0 blocking findings.

## Allowed paths

```text
desktop/controllers/appointment_controller.py
desktop/controllers/schedule_controller.py
desktop/views/main_window.py
agent_reports/**
```

## Forbidden paths

```text
desktop/views/day_view.py
desktop/views/week_view.py
desktop/views/requests_panel.py
desktop/views/blockout_panel.py
desktop/views/settings_panel.py
desktop/controllers/blockout_controller.py
desktop/controllers/settings_controller.py
desktop/controllers/request_controller.py
desktop/controllers/print_controller.py
src/dentaland/services/**
models.py
migrations/**
backend/**
```

**Risk: MEDIUM, ne LOW** — dira konstruktor dijeljene klase
(`AppointmentController`) korišćene na 4 mjesta, iako su default
vrijednosti dizajnirane da tri od četiri ostanu netaknuta. Greška u
default-ima bi tiho promijenila ponašanje REF-09/REF-10 potrošača bez
očiglednog simptoma (doctor state bi i dalje vraćao prazne vrijednosti,
ali sad "namjerno" umjesto "greškom" — razlika je suptilna, vrijedi
review pažnje).

## Review

Codex pa Claude, human approval prije merge-a. Codex treba posebno
provjeriti da `day_view.py`/`week_view.py`/`requests_panel.py` STVARNO
nisu dirani (jer default provideri to omogućavaju) i da postojeći testovi
za `on_slot_selected`/`edit_appointment` (koji čitaju doctor state) i
dalje prolaze identično sa novim provider-baziranim čitanjem.

## Koordinacija

Nema zavisnosti — main je na `9db1cb7`. Nulto preklapanje sa REF-15
(SARAJEVO inline cleanup, dira samo `src/dentaland/services/**` i
`requests_panel.py`) — mogu ići paralelno.
