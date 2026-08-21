---
task_id: FIX-02
reviewer: claude
risk: LOW
verdict: PASS
date: 2026-08-21
---

# Review — FIX-02 (edit trajanja termina, LOW)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

## Scope — PASS

`git status --short` u worktree-u prije commit-a: samo
`desktop/views/dialogs/appointment_editor.py` i
`tests/test_gui/test_appointment_dialog.py` (+ novi, netrekovan
`agent_reports/2026-08-21-FIX-02-pi.md`). Sve unutar `allowed_paths` iz
`agent_reports/FIX-02-task-contract.md`. Nema dodira na
`forbidden_paths` (models.py, migrations/, booking.py, base_dialog.py,
week_view.py, day_view.py, main_window.py).

## Fix — PASS, minimalan i tačan

Diff je tačno predloženo rješenje iz kontrakta: inicijalni poziv
`_apply_service_duration(...)` uslovljen sa `not is_edit`. `connect()` na
`currentIndexChanged` ostaje bezuslovan — ručna promjena usluge i dalje
radi u oba moda.

## Adversarna provjera (nezavisna reprodukcija, ne oslanjanje na izvještaj)

1. Pokrenuo `pytest tests/test_gui/test_appointment_dialog.py -v` na
   fix-ovanom kodu → 13/13 passed, uključujući oba nova testa.
2. **Namjerno vratio bag** (uslov nazad na bezuslovni
   `if self.service_combo.count():`) i ponovo pokrenuo iste testove →
   oba nova testa PADAJU tačno na opisanom simptomu
   (`assert 60 == 90`, `AssertionError` na `duration_edit.value()`).
   Ovo potvrđuje da testovi stvarno hvataju regresiju, ne prolaze
   trivijalno.
3. Vratio fix, ponovo pokrenuo — 13/13 passed.

**Napomena o incidentu tokom review-a:** korak 2 je urađen tako što sam
privremeno editovao fajl, pa pokušao vratiti originalno stanje sa
`git checkout -- appointment_editor.py`. Pošto Pi-jeva izmjena nikad
nije bila commitovana, taj `checkout` je vratio fajl na zadnji
**commitovan** (predbug) kod, ne na Pi-jev fix — čime sam nenamjerno
privremeno obrisao Pi-jev fix sa diska. Odmah uočeno i ispravljeno:
fix ručno ponovo primijenjen (identičan diff, potvrđeno
`git diff` prije/poslije), zatim ponovljena puna verifikacija. Krajnje
stanje radnog stabla je ispravno i verifikovano — vidi rezultate ispod.
Pouka za sljedeći sličan review: kad je izmjena implementera
uncommitted, adversarnu provjeru raditi kroz kopiju fajla (ili `git
stash`), nikad kroz `git checkout --` na necommitovanom stanju.

## Edge case razmotren (ne blokira)

`_prefill()` koristi `getattr(appointment, "end", None)` — ako bi
pozivalac ikad proslijedio edit-mode `appointment` bez `end`, novi kod
ostavlja `duration_edit` na Qt početnoj vrijednosti (min 5) umjesto da
padne nazad na default usluge (staro ponašanje). Provjereno: jedini
stvarni pozivaoci su `desktop/views/main_window.py:560,599`, oba
prosljeđuju `AppointmentDTO` gdje su `start`/`end` obavezna
(non-optional) polja u `services/booking.py` — scenario nije dostižan u
produkciji, samo teorijski kroz duck-typed `Any` parametar (koji
postoji radi testabilnosti). Ne blokira merge, samo zabilježeno.

## Verifikacija (ponovljena nezavisno, na finalnom stanju)

```text
pytest tests/ -q                              → 256 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 35 source files
```

Poklapa se sa Pi-jevim izvještajem (256 = 254 baseline + 2 nova testa).

## Zaključak

Acceptance kriteriji iz kontrakta ispunjeni: edit mode čuva stvarno
trajanje, ručna promjena usluge i dalje radi, create mode nepromijenjen
(postojeći `test_trajanje_se_predlaze_iz_usluge` netaknut i i dalje
prolazi). Scope čist. Fix je minimalan, tačno onakav kakav je kontrakt
predložio. **PASS.** LOW risk — po tabeli u
`docs/dentaland-agentski-razvoj.md` human approval nije obavezan, ali
ostavljam Radovanu odluku da li ga ipak traži.

## Handoff

```text
CILJ: edit mode čuva stvarno trajanje termina umjesto da ga prepiše
      defaultom usluge; create mode nepromijenjen.
URAĐENO: PASS — fix i testovi tačni, adversarno potvrđeno (bug
      reprodukovan i zatvoren), pun gate zelen.
NE DIRATI: schema/migracije, booking.py, base_dialog.py, week_view.py,
      day_view.py, main_window.py — ništa od toga nije ni dirano.
SLJEDEĆE: commit (2 fajla + oba agent_report-a) i merge u main, čim
      Radovan potvrdi. Zatim FIX-01 (DayView blockout, MEDIUM).
```
