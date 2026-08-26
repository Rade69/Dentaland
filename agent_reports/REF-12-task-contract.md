---
task_id: REF-12
risk: LOW
implementer: crush
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit b5006c9, 2026-08-26), post-merge integration gate PASS (368 pytest, ruff, mypy)."
review_summary: >-
  Codex: PASS na prvi pokusaj (implementer proaktivno dodao 4 runtime
  spy testa + 2 unit testa po REF-11 obrascu, adversarno dokazano da
  nijedna od 4 F3 regresije ne daje lazan PASS). Claude: PASS bez
  rezervi - cist facade, isti oblik kao BlockoutController. Preporuka:
  sad kad postoje 3 instance istog self-contained-facade obrasca
  (RequestController/BlockoutController/SettingsController), dokumentovati
  ga eksplicitno u planu/PROJECT_MAP.md kao imenovan Controller-oblik
  (follow-up, ne blokira).
created_at: 2026-08-25
merged_at: 2026-08-26
---

# REF-12 — Nov `SettingsController` za postavke (F3)

## Kontekst

Finalni acceptance audit REF-00..08
(`agent_reports/2026-08-25-REF-FINAL-acceptance-review-codex.md` +
`-claude.md`, oba nezavisno potvrdila) nalaz **F3**:
`desktop/views/settings_panel.py` (`SettingsPanel`) poziva četiri store
mutacije **direktno**, nema Controller sloja:

```text
settings_panel.py:161  self.store.set_doctor_active(doctor_id, active)
settings_panel.py:224  self.store.add_service(naziv, trajanje, buffer)
settings_panel.py:242  self.store.update_service(service_id, naziv, trajanje, buffer)
settings_panel.py:338  self.store.set_working_hours(doctor_id, dan, intervals)
```

Radovanova odluka (25.8.2026): nema prihvaćenog duga, svaki nalaz odmah
postaje task.

## Cilj

Nov `desktop/controllers/settings_controller.py`, `SettingsController`
klasa — **čista delegacija (facade), bez logike**, isti obrazac kao
REF-11-ov `BlockoutController`:

```python
class SettingsController:
    def __init__(self, store: Any) -> None:
        self._store = store

    def set_doctor_active(self, doctor_id, active):
        return self._store.set_doctor_active(doctor_id, active)

    def add_service(self, naziv, trajanje_min, buffer_min):
        return self._store.add_service(naziv, trajanje_min, buffer_min)

    def update_service(self, service_id, naziv, trajanje_min, buffer_min):
        return self._store.update_service(service_id, naziv, trajanje_min, buffer_min)

    def set_working_hours(self, doctor_id, dan, intervals):
        return self._store.set_working_hours(doctor_id, dan, intervals)
```

**Obrazac konstrukcije: `SettingsPanel` konstruiše SVOJU privatnu
`SettingsController` instancu** — `self._settings_controller =
SettingsController(store)` u `__init__`, isti REF-07/REF-11 presedan
(`RequestController`/`BlockoutController`, oba konstruisana unutar
sopstvenog panela, bez `main_window.py` wiring-a). `SettingsPanel.__init__`
već prima samo `store` (provjereno, `settings_panel.py:109`) — nema
potrebe dirati `main_window.py`.

Sva četiri poziv-mjesta mijenjaju SAMO receiver (`self.store.X` →
`self._settings_controller.X`) — **postojeći `try`/`except ValueError` +
`QMessageBox.warning` + `refresh()`/`changed.emit()` ostaju NETAKNUTI**,
Controller je namjerno tanak i ne hvata izuzetke sam.

## Acceptance

- [ ] `settings_panel.py` više ne sadrži nijedan od četiri direktna
      `self.store.*` mutacijska poziva;
- [ ] `grep -n "self\.store\.\(set_doctor_active\|add_service\|update_service\|set_working_hours\)" desktop/views/settings_panel.py`
      daje 0 pogodaka;
- [ ] postojeći GUI/unit testovi za doctor toggle / add-edit service /
      working hours i dalje prolaze bez izmjene ponašanja;
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti.

## Allowed paths

```text
desktop/controllers/settings_controller.py    (novo)
desktop/views/settings_panel.py
agent_reports/**
```

## Forbidden paths

```text
desktop/views/main_window.py
desktop/views/blockout_panel.py
desktop/views/requests_panel.py
desktop/views/day_view.py
desktop/views/week_view.py
desktop/controllers/appointment_controller.py
desktop/controllers/schedule_controller.py
desktop/controllers/blockout_controller.py
src/dentaland/services/**
models.py
migrations/**
backend/**
```

Nulto preklapanje sa REF-09/REF-11/REF-13 je namjerno — omogućava
paralelan rad (plan iz razgovora sa Radovanom, 25.8.2026).

## Review

Codex pa Claude, human approval prije merge-a.

## Koordinacija

Namijenjen za paralelan rad uz REF-11 (i/ili REF-09, REF-13) — nema
zajedničkih `allowed_paths` sa njima, provjereno prije pisanja ovog
kontrakta.
