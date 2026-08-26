---
task_id: REF-13
risk: LOW
implementer: pi
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit 383745d, 2026-08-26), post-merge integration gate PASS (372 pytest, ruff, mypy)."
review_summary: >-
  Codex: PASS_WITH_NOTES (bez blocking nalaza; potvrdio test-kompatibilnost
  temeljno, ispravio nijansu o monkeypatch riziku iz samog kontrakta -
  `from X import Y` i dalje pravi patchable modul-level ime). Claude: PASS
  - cist mehanicki import swap, bez skrivenog ponasanja. Oba potvrdila
  OUT_OF_SCOPE_FINDING (4 inline ZoneInfo poziva) kao tacan, buduci
  REF-XX kandidat.
created_at: 2026-08-25
merged_at: 2026-08-26
---

# REF-13 — Konsolidacija preostalih 9 `SARAJEVO` redefinicija

## Kontekst

REF-08 (`agent_reports/REF-08-task-contract.md`) je konsolidovao 6 mjesta
koja su UVOZILA `SARAJEVO` iz `desktop.fake_data` u `src/dentaland/timezone.py`
(jedina kanonska definicija), ali je EKSPLICITNO ostavio 9 dodatnih mjesta
koja `SARAJEVO = ZoneInfo("Europe/Sarajevo")` **nezavisno redefinišu**
(doslovno kopiraju istu liniju, ne uvoze) kao `OUT_OF_SCOPE_FINDING` —
prijavljeno, namjerno ne dirano, kandidat za budući task.

Radovanova odluka (25.8.2026): nema prihvaćenog duga, svaki poznat nalaz
odmah postaje task. Ovo je taj task.

Ponovo provjereno grep-om 25.8.2026 (i dalje tačno, 9 mjesta):

```text
src/dentaland/services/notifications.py
src/dentaland/services/print_schedule.py
desktop/views/dialogs/appointment_details.py
desktop/views/dialogs/appointment_editor.py
desktop/views/dialogs/cancel_appointment.py
desktop/views/dialogs/delete_appointment.py
desktop/views/dialogs/move_appointment.py
desktop/views/dialogs/process_request.py
desktop/views/requests_page.py
```

## Cilj

Svih 9 mjesta zamjenjuje `SARAJEVO = ZoneInfo("Europe/Sarajevo")` (lokalna
redefinicija) sa `from dentaland.timezone import SARAJEVO` (uvoz iz
kanonskog izvora) — identičan obrazac kao REF-08-ovih 6 mjesta, samo
nastavak na preostalih 9. Behavior-preserving — `ZoneInfo("Europe/Sarajevo")`
je isti objekat po vrijednosti, samo jedan izvor istine umjesto 10 kopija.

Nakon ovog taska: `grep -rn "SARAJEVO = ZoneInfo" src desktop --include=*.py`
smije pokazati TAČNO JEDAN pogodak — `src/dentaland/timezone.py` sam.
(Test fajlovi koji nezavisno definišu `SARAJEVO` kao lokalni fixture su VAN
scope-a — testovi ne moraju importovati produkcijski modul, to nije isti
problem kao produkcijski kod koji duplira izvor istine.)

## Acceptance

- [ ] svih 9 navedenih produkcijskih fajlova uvozi `SARAJEVO` iz
      `dentaland.timezone`, ne redefiniše ga;
- [ ] `grep -rn "SARAJEVO = ZoneInfo" src desktop --include=*.py` → tačno 1
      pogodak (`src/dentaland/timezone.py`);
- [ ] `pytest tests/ -q`, `ruff check`, `mypy` čisti — posebno provjeriti
      da nijedan test koji monkeypatch-uje `SARAJEVO` na starom mjestu
      (npr. `desktop.views.dialogs.appointment_details.SARAJEVO`) nije
      tiho pokvaren zamjenom uvoza (ako testovi importuju/patch-uju
      `SARAJEVO` direktno iz dialoga, provjeriti da patch i dalje pogađa
      efektivnu vrijednost koju kod koristi — ako `from X import Y` obrazac
      znači da patch na starom modulu više ne djeluje, to je legitiman
      `OUT_OF_SCOPE_FINDING` za testove, ne razlog da se stane).

## Allowed paths

```text
src/dentaland/services/notifications.py
src/dentaland/services/print_schedule.py
desktop/views/dialogs/appointment_details.py
desktop/views/dialogs/appointment_editor.py
desktop/views/dialogs/cancel_appointment.py
desktop/views/dialogs/delete_appointment.py
desktop/views/dialogs/move_appointment.py
desktop/views/dialogs/process_request.py
desktop/views/requests_page.py
agent_reports/**
```

**Ne dirati `src/dentaland/timezone.py`** — već postoji, već ispravan,
ovaj task ga samo koristi.

## Forbidden paths

```text
desktop/views/main_window.py
desktop/views/day_view.py
desktop/views/week_view.py
desktop/views/blockout_panel.py
desktop/views/settings_panel.py
desktop/views/requests_panel.py
desktop/controllers/**
src/dentaland/services/appointments.py
src/dentaland/services/availability.py
src/dentaland/services/settings.py
src/dentaland/services/requests.py
models.py
migrations/**
backend/**
```

Nulto preklapanje sa REF-09/REF-11/REF-12 je namjerno — omogućava
paralelan rad (plan iz razgovora sa Radovanom, 25.8.2026). Ovaj task je
mehanički, najniži rizik od sva četiri paralelna kandidata (nema nove
klase, samo import swap na 9 mjesta).

## Review

Codex pa Claude, human approval prije merge-a.

## Koordinacija

Namijenjen za paralelan rad uz REF-09/REF-11/REF-12 — nema zajedničkih
`allowed_paths` sa njima, provjereno prije pisanja ovog kontrakta.
