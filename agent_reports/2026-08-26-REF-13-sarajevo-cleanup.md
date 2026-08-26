---
task_id: REF-13
risk: LOW
implementer: pi
reviewers: [codex, claude]
status: "IMPLEMENTED — čeka review. Bez commit-a (eksplicitna instrukcija: čekati Radovanov zahtjev)."
verification: "pytest 368 passed, ruff All checks passed, mypy no issues in 52 files."
created_at: 2026-08-26
---

# REF-13 — Implementer izvještaj (Pi)

## Šta je urađeno

Svih 9 produkcijskih fajlova koji su nezavisno redefinisali
`SARAJEVO = ZoneInfo("Europe/Sarajevo")` sada uvozi `SARAJEVO` iz kanonskog
`src/dentaland/timezone.py` (mehanički import swap, behavior-preserving —
isti `ZoneInfo` objekat po vrijednosti, jedan izvor istine).

## Mapping (9 fajlova)

| Fajl | Izmjena |
|---|---|
| `src/dentaland/services/notifications.py` | `from zoneinfo import ZoneInfo` + lokalna def → `from dentaland.timezone import SARAJEVO` |
| `src/dentaland/services/print_schedule.py` | isto |
| `desktop/views/dialogs/appointment_details.py` | isto |
| `desktop/views/dialogs/appointment_editor.py` | isto |
| `desktop/views/dialogs/cancel_appointment.py` | isto |
| `desktop/views/dialogs/delete_appointment.py` | isto |
| `desktop/views/dialogs/move_appointment.py` | isto |
| `desktop/views/dialogs/process_request.py` | isto |
| `desktop/views/requests_page.py` | isto |

`from zoneinfo import ZoneInfo` je uklonjen iz svih 9 (nijedan fajl ga više
ne koristi — potvrđeno grep-om, ruff F401/F821 čist).

## Acceptance

- [x] svih 9 fajlova uvozi iz `dentaland.timezone`;
- [x] `grep -rn "SARAJEVO = ZoneInfo" src desktop --include=*.py` → **tačno 1**
      pogodak: `src/dentaland/timezone.py:12`;
- [x] `pytest`, `ruff`, `mypy` čisti;
- [x] test monkeypatch provjera: **nema** testa koji patch-uje `.SARAJEVO` na
      bilo kom od 9 modula, niti direktnog `from ... import SARAJEVO` iz ovih
      9 modula (grep-ano `\.SARAJEVO` i specifični import patterni u `tests/`).
      Test fajlovi sa lokalnim `SARAJEVO = ZoneInfo(...)` fixture-om
      (`test_destructive_dialogs.py`, `test_print_schedule.py`) su VAN scope-a
      po kontraktu i netaknuti.

## OUT_OF_SCOPE_FINDING — inline `ZoneInfo("Europe/Sarajevo")` pozivi

Kontrakt pokriva samo `SARAJEVO = ZoneInfo(...)` redefinicije. Grep je otkrio
**dodatni oblik** istog duga — inline `ZoneInfo("Europe/Sarajevo")` pozive
(bez `SARAJEVO` konstante) na 4 mjesta u 3 fajla:

```yaml
finding: OUT_OF_SCOPE_FINDING
description: >
  Inline ZoneInfo("Europe/Sarajevo") pozivi (ne kroz SARAJEVO konstantu) —
  isti izvor-istine problem u drugom obliku, ali u forbidden_paths REF-13.
locations:
  - src/dentaland/services/appointments.py:336
  - src/dentaland/services/availability.py:96
  - src/dentaland/services/availability.py:119
  - desktop/views/requests_panel.py:121
risk: LOW
proposed_task: REF-XX — zamijeniti inline ZoneInfo("Europe/Sarajevo") sa
  dentaland.timezone.SARAJEVO na ova 4 mjesta.
```

Ne dirano (sva 3 fajla su `forbidden_paths` za REF-13).

## Verifikacija (doslovni rezultati)

```text
$ python -m pytest tests/ -q
368 passed, 11 warnings in 16.30s

$ python -m ruff check src/dentaland desktop backend tests
All checks passed!

$ python -m mypy src/dentaland desktop backend
Success: no issues found in 52 source files
```

## Nije urađeno / namjerno izostavljeno

- Nema commit-a — čekam Radovanov zahtjev.
- `src/dentaland/timezone.py` nije diran (već ispravan).
- 4 inline `ZoneInfo("Europe/Sarajevo")` poziva (OUT_OF_SCOPE_FINDING) nisu
  dirani.
- Test fajlovi sa lokalnim `SARAJEVO` fixture-om nisu dirani (van scope-a po
  kontraktu).
