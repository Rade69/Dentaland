---
task_id: REF-15
risk: LOW
implementer: crush
reviewers: [codex, claude]
status: "READY FOR REVIEW — implementacija + verifikacija gotovi (374 pytest, ruff, mypy čisti, agent_sensors 0 findings). NIJE commitovano."
created_at: 2026-08-26
---

# REF-15 — Konsolidacija preostalih 4 inline ZoneInfo (implementer izvještaj)

## Šta je urađeno

Po Task Contract-u (`agent_reports/REF-15-task-contract.md`), čisto mehanička
izmjena — sva 4 inline `ZoneInfo("Europe/Sarajevo")` poziva zamijenjena sa
`SARAJEVO` iz `dentaland.timezone`, i uklonjen `from zoneinfo import ZoneInfo`
iz sva 3 fajla (postao neiskorišten).

```text
src/dentaland/services/appointments.py:336   zone = SARAJEVO
src/dentaland/services/availability.py:96     zone = SARAJEVO
src/dentaland/services/availability.py:119    zone = SARAJEVO
desktop/views/requests_panel.py:121           appt.start.astimezone(SARAJEVO)
```

Svaki fajl dobio `from dentaland.timezone import SARAJEVO` (dodat u postojeći
import blok, nema duplog importa). Lokalne `zone` varijable zadržane
(minimalna behavior-preserving izmjena, kako contract dozvoljava).

## Acceptance dokaz (stvaran output)

```text
$ grep -rn 'ZoneInfo("Europe/Sarajevo")' src desktop --include=*.py
src/dentaland/timezone.py:12: SARAJEVO = ZoneInfo("Europe/Sarajevo")   # kanonska definicija (jedina)

$ grep -rn "SARAJEVO = ZoneInfo" src desktop --include=*.py
src/dentaland/timezone.py:12                                             # tačno 1 (kanonska)
```

Nema inline `ZoneInfo("Europe/Sarajevo")` van `timezone.py`; kanonska
definicija netaknuta.

## Verifikacija (stvaran output)

```text
$ python -m pytest tests/ -q
374 passed, 11 warnings in 18.85s

$ ruff check src/dentaland desktop backend tests scripts/agent_sensors.py
All checks passed!

$ mypy src/dentaland desktop backend
Success: no issues found in 52 source files

$ python scripts/agent_sensors.py --all
Result: 0 blocking findings
```

## Dirnuti fajlovi

```text
M  src/dentaland/services/appointments.py
M  src/dentaland/services/availability.py
M  desktop/views/requests_panel.py
A  agent_reports/2026-08-26-REF-15-sarajevo-inline-cleanup.md
```

Nedirano: `src/dentaland/timezone.py` (kanonska definicija), i svi forbidden
paths.

## OUT_OF_SCOPE_FINDING

Nema.

## Napomena

NIJE commitovano/pušovano (po instrukciji). Claim oslobođen
(`coordination.py release --task REF-15`).
