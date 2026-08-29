---
task_id: REF-16
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit 3c51856, 29.8.2026). Codex + Claude PASS (bez rezervi). Post-merge integration gate PASS (429 pytest, ruff, mypy, agent_sensors čisti). Zatvara cijeli Prioritet C backlog."
created_at: 2026-08-26
---

# REF-16 — Kida cirkularni import main_window ↔ appointment_controller

## Kontekst

Dokumentovan dug (`.agent/CURRENT_STATE.md`, stavka (1) iz "Controller gleda
nazad u View"): `AppointmentController` lazy-uvozi Dialog klase iz
`desktop.views.main_window` unutar metoda, a `main_window.py` zauzvrat
top-level importuje `AppointmentController` (linija 32) i re-eksportuje 5
dijalog klasa isključivo radi tog lazy importa i GUI-test monkeypatch-a.
Rezultat je logički ciklus `main_window ↔ appointment_controller`.

Nije nemar — komentar u `appointment_controller.py` eksplicitno objašnjava
da je to tako jer postojeći GUI testovi monkeypatch-uju dijaloge na
`desktop.views.main_window` modulu.

**Istraženo prije pisanja kontrakta:** `desktop/views/dialogs/__init__.py`
VEĆ postoji i već re-eksportuje svih 5 potrebnih klasa (plus `BaseDialog`,
`BlockoutDeleteConfirmDialog`, `ProcessRequestDialog`). Dijalozi ne zavise
ni od `main_window` ni od `appointment_controller`. Zato se ciklus kida
PREUSMJERAVANJEM importa na postojeći registry, ne kreiranjem novog modula.

## Cilj

1. `appointment_controller.py` — 6 lazy importa preusmjeriti sa
   `desktop.views.main_window` na `desktop.views.dialogs`; ažurirati
   docstring koji opisuje stari mehanizam.
2. `main_window.py` — obrisati re-eksport blok (komentar + 5 `noqa: F401`
   import linija dijalog klasa). Linija 30 (`OverlapError`, "REF-00
   baseline") NIJE dio ovog zadatka i ostaje.
3. GUI testovi koji patch-uju dijaloge na `main_window` modulu preusmjeriti
   na `desktop.views.dialogs` modul — tačno 11 `monkeypatch.setattr`
   poziva (3 u `test_appointment_controller.py`, 8 u `test_main_window.py`).

## Acceptance

- [ ] `appointment_controller.py` nema nijedan
      `from desktop.views.main_window import ...` — svih 6 lazy importa ide
      iz `desktop.views.dialogs`;
- [ ] `main_window.py` više ne re-eksportuje dijalog klase (5 `noqa: F401`
      linija uklonjeno), `OverlapError` re-eksport (REF-00 baseline) ostaje;
- [ ] `monkeypatch.setattr(main_window_mod, "<Dijalog>", ...)` više ne
      postoji u testovima — svih 11 preusmjereno na `dialogs_mod`;
- [ ] postojeći GUI testovi prolaze identično (baseline 37 passed na 2
      dirnuta fajla);
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti;
- [ ] `python scripts/agent_sensors.py --all` i dalje 0 blocking findings.

## Allowed paths

```text
desktop/controllers/appointment_controller.py
desktop/views/main_window.py
tests/test_gui/test_appointment_controller.py
tests/test_gui/test_main_window.py
agent_reports/**
```

## Forbidden paths

```text
desktop/views/dialogs/** (samo čitanje — modul se koristi, ne mijenja)
src/dentaland/services/**
models.py
migrations/**
backend/**
```

**Risk: MEDIUM** — arhitektonski refaktor koji dira `desktop/controllers/`,
`desktop/views/main_window.py` i test fajlove. Nije schema/security (nije
HIGH). Mehanički po prirodi, ali test monkeypatch preusmjeravanje mora biti
tačno (patch cilj mora biti modul sa kojeg controller stvarno importuje),
inače testovi tiho postaju lažni PASS.

## Review

Codex pa Claude, human approval prije merge-a. Codex treba posebno
provjeriti da (a) nijedan test i dalje ne patchuje `main_window_mod` za
dijaloge (jer bi to bio lažan patch — controller više ne gleda tamo), i
(b) `test_main_window.py` i dalje ispravno koristi `main_window_mod` za
ne-dijalog stvari (`MainWindow`, `QPushButton`, `QInputDialog`,
`DOCTOR_AVATAR_SIZE`).

## Koordinacija

Nema zavisnosti — bazirano na `main` (`1cd4324`). Nulto preklapanje sa
drugim taskovima; samo `main_window.py` se dira, a taj fajl nije u
`allowed_paths` nijednog drugog aktivnog REF taska.
