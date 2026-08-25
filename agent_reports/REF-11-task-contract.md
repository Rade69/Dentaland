---
task_id: REF-11
risk: LOW
implementer: TBD
reviewers: [codex, claude]
status: "OPEN — task contract napisan prije koda"
created_at: 2026-08-25
---

# REF-11 — Nov `BlockoutController` za TimeOff/blockout (F2)

## Kontekst

Finalni acceptance audit REF-00..08
(`agent_reports/2026-08-25-REF-FINAL-acceptance-review-codex.md` +
`-claude.md`, oba nezavisno potvrdila) nalaz **F2**:
`desktop/views/blockout_panel.py` (`BlockoutPanel`) poziva
`self.store.create_time_off(...)`/`self.store.delete_time_off(...)`
**direktno** na linijama 181 i 195 — nema Controller sloja.

Radovanova odluka (25.8.2026): nema prihvaćenog duga, svaki nalaz odmah
postaje task.

## Cilj

Nov `desktop/controllers/blockout_controller.py`, `BlockoutController`
klasa — **čista delegacija (facade), bez logike**, po uzoru na
`src/dentaland/services/booking.py`-ov REF-03 facade obrazac:

```python
class BlockoutController:
    def __init__(self, store: Any) -> None:
        self._store = store

    def create_time_off(self, doctor_id, start, end, reason):
        return self._store.create_time_off(doctor_id, start, end, reason)

    def delete_time_off(self, block_id):
        return self._store.delete_time_off(block_id)
```

**Obrazac konstrukcije: `BlockoutPanel` konstruiše SVOJU privatnu
`BlockoutController` instancu** — `self._blockout_controller =
BlockoutController(store)` u `__init__`, analogno `self._request_controller
= RequestController(store)` (`requests_panel.py:29`, REF-07 presedan).
**Namjerno NE dira `main_window.py`** — `BlockoutPanel.__init__` već prima
samo `store` (provjereno, nema MainWindow-specifičnog stanja), pa nema
potrebe za wiring-om izvan ovog fajla.

`blockout_panel.py:180-187` i `:189-200` mijenjaju SAMO poziv (`self.store.X`
→ `self._blockout_controller.X`) — **postojeći `try`/`except`
(`OverlapError`/`ValueError`) i `_show_error`/`refresh`/`changed.emit()`
ostaju NETAKNUTI**, to je View-specifična prezentacija greške (inline forma,
ne dijalog), Controller je namjerno tanak i ne hvata izuzetke sam.

## Acceptance

- [ ] `blockout_panel.py` više ne sadrži `self.store.create_time_off`/
      `self.store.delete_time_off` pozive;
- [ ] `grep -n "self\.store\." desktop/views/blockout_panel.py` ne
      pokazuje mutacijske pozive;
- [ ] postojeći GUI/unit testovi za blockout create/delete i dalje
      prolaze bez izmjene ponašanja;
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti.

## Allowed paths

```text
desktop/controllers/blockout_controller.py    (novo)
desktop/views/blockout_panel.py
agent_reports/**
```

## Forbidden paths

```text
desktop/views/main_window.py
desktop/views/settings_panel.py
desktop/views/requests_panel.py
desktop/views/day_view.py
desktop/views/week_view.py
desktop/controllers/appointment_controller.py
desktop/controllers/schedule_controller.py
desktop/controllers/settings_controller.py
src/dentaland/services/**
models.py
migrations/**
backend/**
```

Nulto preklapanje sa REF-09/REF-12/REF-13 je namjerno — omogućava
paralelan rad (plan iz razgovora sa Radovanom, 25.8.2026).

## Review

Codex pa Claude, human approval prije merge-a.

## Koordinacija

Namijenjen za paralelan rad uz REF-12 (i/ili REF-09, REF-13) — nema
zajedničkih `allowed_paths` sa njima, provjereno prije pisanja ovog
kontrakta.
