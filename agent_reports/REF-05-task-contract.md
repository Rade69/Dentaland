---
task_id: REF-05
risk: MEDIUM
implementer: crush
reviewers: [codex, claude]
status: "READY FOR REVIEW — implementacija + verifikacija gotovi (347 pytest, ruff, mypy čisti). O1 primijenjen: test_week_view_combined.py dodat u obim."
review_summary: ""
created_at: 2026-08-24
merged_at: ""
---

# REF-05 — Scheduler Controller + refresh orchestration

## Task Contract

**Cilj:** `MainWindow` prestaje koordinirati Day/Week state, doctor filter,
schedule refresh, status summary i doctor counts. Uvodi se
`ScheduleController` koji fetch-uje jedan snapshot po refresh-u i prosleđuje
ga aktivnom view-u kroz novu `render(appointments, blocks)` metodu; view
prestaje sam fetch-ovati.

**Risk:** MEDIUM (prvi task koji menja KAKO scheduler view dobija podatke;
dvostruki review za REF paket).

Izvor: `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`, sekcija 12.

Zavisnost: REF-02 (`appointments_for_range`) + REF-04 (`AppointmentController`)
— potvrđeno mergovan (main HEAD `daf3074`).

## Dokazan problem (potvrđen čitanjem koda, ne nagađanje)

`MainWindow._refresh_dashboard()` (main_window.py:384) poziva
`week_view.refresh()` I `day_view.refresh()` OBA bez obzira na aktivan tab,
pa `_update_status_legend()` → `_update_doctor_panel_counts()` poziva
`view.visible_status_counts()` i `view.visible_doctor_counts()` na aktivnom
view-u.

U `week_view.py`: `visible_status_counts()` → `_visible_appointments()` →
`_fetch_appointments()` (fetch #1); `visible_doctor_counts()` →
`_fetch_appointments()` direktno (fetch #2); `refresh()` →
`_visible_appointments()` → fetch #3. Dakle minimalno 3 identična
`appointments_for_range` fetch-a u jednom refresh ciklusu, samo za WeekView,
plus `_fetch_blocks()`. `day_view.py` ima analogan obrazac (provjereno:
`_fetch_appointments`, `_fetch_blocks`, `visible_status_counts`,
`visible_doctor_counts`, `_appointments_by_cell` svi fetch-uju).

## Arhitektonska promjena

1. **View prestaje fetch-ovati** — `_fetch_appointments()`/`_fetch_blocks()`
   interni store pozivi se uklanjaju. View dobija dataset kroz
   `render(appointments, blocks)` i čuva ga u cache (`_appointments`/
   `_blocks`). `refresh()` postaje interni re-draw iz cache-a, bez fetch-a.
   `visible_status_counts()`/`visible_doctor_counts()` računaju iz ISTOG
   cache-a (bez ponovnog fetch-a).
2. **`ScheduleController`** (novo, `desktop/controllers/`) drži state
   (`week_start`, `current_day`, `_current_doctor_id`), radi jedan
   `appointments_for_range` + jedan `time_off_for_week`/`breaks_for_week`
   po refresh-u, poziva `active_view.render(...)`, i iz ISTOG dataseta
   računa status counts + doctor counts (callback-ovi ka `MainWindow`).
3. **`MainWindow`** delegira `_move_week`/`_go_today`/`_show_day_view`/
   `_show_week_view`/`_on_tab_changed`/schedule-refresh ka controller-u.
   `_refresh_dashboard()` i dalje refreshuje dashboard panels + requests
   page + sidebar pending count (to NISU scheduler view-ovi), ali scheduler
   refresh ide kroz `ScheduleController.refresh()` (samo aktivan view).
   Auto-refresh (20s) poziva isti `_refresh_dashboard()` — sidebar pending
   count ostaje ažuran uvijek, ali se skriveni scheduler view ne fetch-uje.

## Kalendarski blokovi

`calendar_blocks_for_range` iz plana NE postoji — postoje
`time_off_for_week(week_start)`/`breaks_for_week(week_start)` (week-based).
NE dodajem novu servisnu funkciju (servisni sloj nije u scope-u). Controller
poziva postojeće JEDNOM po refresh-u; day view interno filtrira blokove na
svoj dan (presentation, ne fetch).

## ScheduleSnapshot

Koristim običnu torku/dict (plan eksplicitno dozvoljava), ne formalni
dataclass.

## Obim izmjene GUI testova (pregledano prije koda)

Postojeći `test_week_view.py`/`test_day_view.py` mock-uju store ili koriste
pravi servis i oslanjaju se na to da view SAM fetch-uje u `__init__`/
`refresh()`. Promjena na injected-dataset model zahtijeva ažuriranje tih
testova da pozivaju `view.render(...)` umjesto `view.refresh()`, ili da
render-uju blokove eksplicitno.

Pogođeno (mehanička zamjena, ne promjena ŠTA se testira):
- `test_week_view.py`: ~12 testova (`refresh()` → `render(...)` ili
  eksplicitan render blokova).
- `test_day_view.py`: ~10 testova (konstrukcija više ne fetch-uje →
  eksplicitan `render(...)`).

Obrazloženje za svaku izmjenu biće u implementer izvještaju. Izmjena je
OPRAVDANA: mijenja se KAKO view dobija podatke (injected dataset), ne ŠTA
prikazuje — GUI prikaz ostaje identičan.

## Acceptance

- [ ] Day/Week state (`current_day`, `week_start`, doctor filter) nije u `MainWindow` workflow logici;
- [ ] jedan scheduler refresh nema višestruke `appointments_for_range` fetch-eve za counts/render (dokaz brojem, ne tvrdnjom);
- [ ] skriveni view (neaktivan tab) se ne refreshuje;
- [ ] status summary i doctor counts ostaju tačni (ista vrijednost, iz jednog dataseta);
- [ ] 20s timer ne pokreće redundantne DB queryje, ali sidebar pending count ostaje ažuran;
- [ ] Evidence: fake-store/query-counter test koji deterministički dokazuje broj fetch poziva PRIJE i POSLIJE (obrazac REF-02).

## Allowed paths

```text
desktop/controllers/schedule_controller.py    (novo)
desktop/controllers/__init__.py
desktop/views/main_window.py
desktop/views/day_view.py
desktop/views/week_view.py
tests/test_gui/test_schedule_controller.py    (novo)
tests/test_gui/test_week_view.py              (izmjene, obrazložiti)
tests/test_gui/test_day_view.py               (izmjene, obrazložiti)
tests/test_gui/test_week_view_combined.py     (izmjene, obrazložiti — O1, dodat u obim 24.8.)
agent_reports/**
```

## Forbidden paths

```text
desktop/controllers/appointment_controller.py   (REF-04, ne diram)
desktop/views/dialogs/**
src/dentaland/services/**                       (servisni sloj, ne diram)
backend/**
models.py
migrations/**
```

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline: **341 pytest passed** (izmjeriti tačan broj na svom worktree-u prije
početka, ne pretpostaviti).

## Review

Codex (test kvalitet, prvi) pa Claude (arhitektura). Radovan human approval
obavezan prije merge-a.

## Koordinacija

Worktree `Dentaland-worktrees/REF-05-schedule-controller`, grana
`task/REF-05-schedule-controller` (sa main-a `daf3074`). Claim prije početka.

## Kill/rollback pravilo (plan sekcija 22)

Ako broj dirnutih fajlova poraste >2x iznad allowed_paths (8 fajlova), ili
ako se GUI test izmjene pokažu masovne (npr. zahtijevaju promjenu ŠTA se
testira, ne samo KAKO view dobija podatke), STAJEM i prijavljujem prije
daljeg rada.
