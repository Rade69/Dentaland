---
task_id: REF-15
risk: LOW
implementer: crush
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit 32dafbd, 2026-08-26), post-merge integration gate PASS (374 pytest, ruff, mypy, agent_sensors 0 findings). Zadnji poznat dug iz REF-08/REF-13 lanca zatvoren."
review_summary: >-
  Codex: PASS bez nalaza (potvrdio i ZoneInfo cache identity -
  SARAJEVO is ZoneInfo("Europe/Sarajevo") - dokaz da promjena ne mijenja
  runtime ponasanje). Claude: PASS bez rezervi.
created_at: 2026-08-26
merged_at: 2026-08-26
---

# REF-15 — Konsolidacija preostalih 4 inline `ZoneInfo("Europe/Sarajevo")` poziva

## Kontekst

REF-13 (`agent_reports/REF-13-task-contract.md`, merge `383745d`) je
konsolidovao svih 15 `SARAJEVO = ZoneInfo(...)` **konstanti** u
`dentaland.timezone`, ali je usput otkrio i prijavio (`OUT_OF_SCOPE_FINDING`)
**drugi oblik istog problema** — mjesta koja pozivaju `ZoneInfo("Europe/Sarajevo")`
**inline**, bez `SARAJEVO` konstante uopšte. Radovanova odluka: nema
prihvaćenog duga, ovo se sad zatvara.

Ponovo provjereno grep-om 26.8.2026 (i dalje tačno, 4 mjesta u 3 fajla):

```text
src/dentaland/services/appointments.py:336
src/dentaland/services/availability.py:96
src/dentaland/services/availability.py:119
desktop/views/requests_panel.py:121
```

## Cilj

Sva 4 mjesta zamjenjuju `ZoneInfo("Europe/Sarajevo")` sa `SARAJEVO`
uvezenim iz `dentaland.timezone` — isti obrazac kao REF-13, samo za inline
oblik umjesto imenovane konstante.

**`appointments.py:336`** (u `cancelled_today`):
```python
zone = ZoneInfo("Europe/Sarajevo")
```
→
```python
zone = SARAJEVO
```
(ili još bolje — ukloniti lokalnu `zone` varijablu i koristiti `SARAJEVO`
direktno na mjestima gdje se `zone` koristi; implementer bira minimalniju
izmjenu, oba su prihvatljiva dok god je behavior-preserving).

**`availability.py:96`** (u `time_off_for_week`) i **`availability.py:119`**
(u `breaks_for_week`): isti obrazac — `zone = ZoneInfo("Europe/Sarajevo")` →
`zone = SARAJEVO`.

**`requests_panel.py:121`**:
```python
local = appt.start.astimezone(ZoneInfo("Europe/Sarajevo"))
```
→
```python
local = appt.start.astimezone(SARAJEVO)
```

Svaki od 3 fajla dobija `from dentaland.timezone import SARAJEVO` (ili se
dodaje u postojeći import blok ako `dentaland.timezone` već ima drugi
import u tom fajlu — provjeriti prije dodavanja duplog importa).

**Import cleanup:** `from zoneinfo import ZoneInfo` postaje neiskorišten
u sva 3 fajla nakon ove izmjene (provjereno: to je jedina upotreba
`ZoneInfo` u svakom od njih) — ukloniti taj import, inače `ruff` puca na
unused-import (F401).

## Acceptance

- [ ] sva 4 mjesta koriste `SARAJEVO` iz `dentaland.timezone`, ne
      `ZoneInfo("Europe/Sarajevo")` inline;
- [ ] `grep -rn "ZoneInfo(\"Europe/Sarajevo\")" src desktop --include=*.py`
      → 0 pogodaka (van test fajlova, koji su van scope-a);
- [ ] `grep -rn "SARAJEVO = ZoneInfo" src desktop --include=*.py` i dalje
      tačno 1 pogodak (`src/dentaland/timezone.py`) — ne dirati kanonsku
      definiciju;
- [ ] postojeći testovi za `cancelled_today`/`time_off_for_week`/
      `breaks_for_week`/dashboard prikaz prolaze bez izmjene ponašanja;
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti;
- [ ] `python scripts/agent_sensors.py --all` i dalje 0 blocking findings
      (ovaj task ne dira `desktop/views/**` mutacijske pozive, senzor ne
      bi trebao reagovati — provjeriti da ostane tako).

## Allowed paths

```text
src/dentaland/services/appointments.py
src/dentaland/services/availability.py
desktop/views/requests_panel.py
agent_reports/**
```

**Ne dirati `src/dentaland/timezone.py`** — već postoji, već ispravan.

## Forbidden paths

```text
desktop/views/main_window.py
desktop/views/day_view.py
desktop/views/week_view.py
desktop/views/blockout_panel.py
desktop/views/settings_panel.py
desktop/controllers/**
src/dentaland/services/settings.py
src/dentaland/services/requests.py
src/dentaland/services/notifications.py
src/dentaland/services/print_schedule.py
models.py
migrations/**
backend/**
```

## Review

Standardan REF paket dual-review (Codex pa Claude), human approval prije
merge-a. Ovo je najniže-rizičan preostao task u REF backlogu — čisto
mehanička izmjena, nema arhitektonske odluke.

## Koordinacija

Nema zavisnosti — main je na `9db1cb7`, može krenuti odmah. Nulto
preklapanje sa REF-14 (koji dira `appointment_controller.py`/
`schedule_controller.py`/`main_window.py`) — mogu ići paralelno ako ima
dva implementera dostupna.
