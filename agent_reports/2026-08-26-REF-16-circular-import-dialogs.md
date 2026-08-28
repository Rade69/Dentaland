---
task_id: REF-16
risk: MEDIUM
implementer: pi
reviewers: [codex, claude]
verdict: PENDING_REVIEW
commits: []
created_at: 2026-08-26
---

# REF-16 — Kida cirkularni import main_window ↔ appointment_controller

## Task Contract

Vidi `agent_reports/REF-16-task-contract.md`.

## Šta je urađeno

1. `desktop/controllers/appointment_controller.py`
   - 6 lazy importa preusmjereno: `desktop.views.main_window` →
     `desktop.views.dialogs` (linije 87, 123, 163, 218, 242, 257).
   - Docstring ažuriran — opisuje novi mehanizam i navodi REF-16.
2. `desktop/views/main_window.py`
   - Obrisan re-eksport blok: komentar (2 linije) + 5 `noqa: F401` import
     linija dijalog klasa. `OverlapError` re-eksport (REF-00 baseline,
     linija 30) netaknut.
3. `tests/test_gui/test_appointment_controller.py`
   - Import `main_window as main_window_mod` → `dialogs as dialogs_mod`.
   - 3 `monkeypatch.setattr` preusmjereno na `dialogs_mod`.
4. `tests/test_gui/test_main_window.py`
   - Dodan import `from desktop.views import dialogs as dialogs_mod`
     (abecedno ispred `main_window` — ruff I001).
   - 8 dijalog `monkeypatch.setattr` preusmjereno na `dialogs_mod`.
   - `main_window_mod` zadržan za ne-dijalog upotrebe (`MainWindow`,
     `QPushButton`, `QInputDialog`, `DOCTOR_AVATAR_SIZE`).

## Verifikacija (stvarni rezultati, pokrenuto)

| Provjera | Rezultat |
|---|---|
| `pytest tests/test_gui/test_appointment_controller.py tests/test_gui/test_main_window.py -q` | **37 passed** (baseline identičan) |
| `pytest tests/test_gui/ -q` | **182 passed** |
| `pytest tests/ -q` | **410 passed, 2 skipped** (12 deprecation warnings iz zavisnosti) |
| `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py` | **All checks passed** |
| `mypy src/dentaland desktop backend` | **Success: no issues found in 54 source files** |
| `python scripts/agent_sensors.py --all` | **0 blocking findings** |

Dokaz kidanja ciklusa (`PYTHONPATH=src`):

```text
dialogs import OK
main_window u sys.modules nakon dialogs importa: False
appointment_controller u sys.modules nakon dialogs importa: True
main_window + appointment_controller import OK (bez ciklusa)
dijaloske klase na dialogs modulu: True
dijaloske klase više NISU na main_window modulu: True
```

Grep potvrda: nijedna produkcijska referenca na dijaloge kroz `main_window`
izvan dirnutih fajlova (prazan rezultat).

## Review

Čeka Codex (Reviewer 1) i Claude (Reviewer 2), pa human approval.

## Integration status

`IMPLEMENTED → AWAITING_REVIEW` — nije commitovano, nije mergovano.

## Napomena (nije OUT_OF_SCOPE_FINDING, postojeće stanje)

`desktop/views/dialogs/appointment_details.py` uvozi `STATUS_META,
_status_key` iz `desktop.views.week_view`, a `week_view.py` top-level
importuje `AppointmentController`. Zato `import desktop.views.dialogs`
indirektno učitava `appointment_controller` (ne i `main_window`). Ovo NIJE
import-time ciklus (prvi hop `appointment_controller → dialogs` je lazy, u
tijelu metode) i NIJE pogoršano ovom izmjenom — isti oblik je postojao i
prije (`appointment_controller → main_window → week_view →
appointment_controller`). Direktan ciklus `main_window ↔
appointment_controller` je pokidan; dublji lanac dijalog→week_view je
nezavisna postojeća zavisnost.

## Odbačene opcije

- **Novi `registry.py` modul** — odbačeno jer `desktop/views/dialogs/__init__.py`
  već re-eksportuje svih 5 klasa; novi modul bi bio duplikat.
- **Module-level import dijaloga u controlleru** — odbačeno; zadržan lazy
  import jer GUI testovi patch-uju dijaloge NAKON konstrukcije
  `MainWindow`-a, a late binding to omogućava.
