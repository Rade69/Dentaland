---
task_id: REF-05
risk: MEDIUM
reviewer: claude
implementer: crush
reviewer_role: Reviewer 2 (arhitektura)
previous_review: 2026-08-24-REF-05-review-codex.md (PASS, nakon F1 REJECT runde 1)
verdict: PASS_WITH_NOTES
commits: [7692f31, 8693264]
created_at: 2026-08-24
---

# REF-05 — Claude review (arhitektura, Reviewer 2)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS_WITH_NOTES
blocking_findings: []
```

```text
CILJ: Arhitektonska procjena ScheduleController/View granice i dugoročnog
      troška doctor-state duplikacije (Codex ju je potvrdio bezopasnom
      SADA, ja procjenjujem da li treba formalno zabilježiti kao dug).
URAĐENO: PASS_WITH_NOTES — arhitektura je čista, ali doctor_id state je
      sada duplikovan na TRI mjesta (ne dva kako je REF-04 dug opisivao),
      i to zaslužuje eksplicitno proširenje postojeće CURRENT_STATE
      napomene, ne novi separatan nalaz.
NE DIRATI: servisni sloj, dijaloge, backend, modele, migracije — nedirano.
SLJEDEĆE: Radovanov human approval, pa merge — prije REF-06.
```

## 1. Nezavisna verifikacija (ponovljena)

```text
pytest tests/ -q                              → 349 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 43 source files
```

## 2. Arhitektura `ScheduleController` — potvrđeno čist

Pročitao sam `schedule_controller.py` u cjelini (143 linije). Nema SQL-a,
sav pristup podacima ide kroz `store` facade (`getattr` pozivi, isti
obrazac kao `AppointmentController`). `view_stack.currentWidget()` se
samo čita da odredi aktivan view — ne mutira GUI stanje mimo `_day_view`/
`_week_view` metoda. Direktan uvoz `DayView`/`WeekView` klasa (linije
26-27) je LEGITIMAN — za razliku od REF-04-ovog "lazy import iz
main_window" (koji je rješavao cirkularni import + monkeypatch-timing
problem), ovdje Controller uvozi View module da bi mogao pozivati
njihove javne metode (`set_day`, `set_week_start`, `set_filter`,
`render_schedule`) — nema cirkularne zavisnosti (View ne uvozi
`ScheduleController` nazad), pa nema razloga za lazy binding.

## 3. Doctor state — proširujem Codexov nalaz, ne novi problem

Codex je potvrdio da su `MainWindow._current_doctor_id` i
`ScheduleController._current_doctor_id` sinhronizovani u normalnoj UI
putanji (`_on_tab_changed()` ažurira oba atomarno). Slažem se s tom
provjerom — ponovio sam čitanje `set_doctor_filter()` (linije 139-142) i
potvrđujem da nema puta koji bi ih desinhronizovao u trenutnom kodu.

**Proširenje:** ovo sad NIJE dvostruka duplikacija (REF-04 dug), nego
**trostruka**: `MainWindow._current_doctor_id` (state), koje čita
`AppointmentController` kroz `getattr` (REF-04 dug), PLUS
`ScheduleController._current_doctor_id` (nezavisna kopija, REF-05). Tri
mjesta drže "isti" podatak, sinhronizovana samo zato što je JEDNA UI
putanja (`_on_tab_changed`) disciplinovano ažurira sve odjednom — svaki
budući dodatni put promjene doktora (npr. da REF-06/07/08 doda još jedan
način da se filter mijenja) mora da zna da ažurira SVE TRI, inače
desinhronizacija postaje stvaran bug, ne teoretski.

Ovo ne mijenja verdikt — funkcionalno je ispravno sada, dokazano testom
koji je Codex privremeno napravio i uklonio. Ali vrijedi ažurirati
postojeću REF-04 CURRENT_STATE napomenu ("tehnički dug: Controller gleda
nazad u View") da eksplicitno pomene i ovo TREĆE mjesto — inače će
budući task vidjeti samo dvije lokacije i propustiti treću.

## 4. `render_schedule` naziv — dobra odluka, ne `render`

Potvrđujem Crush-evo obrazloženje (plan predlaže `render(...)`, ali
`QWidget.render(QPainter, ...)` već postoji — kolizija bi dala `mypy`
`[override]` grešku i tiho zasjenila Qt-ovu metodu). `render_schedule` je
jasno ime, izbjegava zamku. Ovo je tačno vrsta odluke koju bi implementer
trebao samostalno donijeti i obrazložiti, ne slijepo pratiti plan
doslovno kad plan koristi ime koje se kosi sa frameworkom.

## 5. F1 fix (8693264) — pregledan, kvalitet potvrđen

Pregledao sam nove integracijske testove koji koriste stvarne `WeekView`/
`DayView` (ne `_FakeView`). Ne ponavljam Codexovu adversarnu verifikaciju
(već dvaput dokazana — originalna regresija na `7692f31`, i potvrđena
popravka na `8693264` sa dvije nezavisne mutacije) — to bi bilo trošenje
tokena na već utvrđeno.

## Zaključak

PASS_WITH_NOTES. `ScheduleController` je arhitektonski čist — jedan
snapshot po refresh-u, dokazano integracijskim testom nad pravim View
klasama, skriveni view se ne renderuje, servisni sloj nedirnut. Jedina
napomena: doctor_id state duplikacija je sada trostruka, ne dvostruka —
preporučujem proširiti postojeću CURRENT_STATE zabilješku (ne novi
zaseban zapis) da budući REF task ima potpunu sliku prije nego što doda
još jedan put promjene doktora. Nema blokirajućih nalaza. Čeka Radovanov
human approval prije merge-a.
