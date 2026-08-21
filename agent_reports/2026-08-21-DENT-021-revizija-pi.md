---
task_id: DENT-021
risk: LOW
implementer: pi
reviewers: [claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-21
---

# DENT-021 (revizija) — Panel doktora: veći avatari + brojčana znaka

## Napomena o Codex-ovoj verziji

Codex-ova prva verzija (necommitovana u glavnom checkout-u) je
`verdict: PASS_WITH_NOTES` i koristi se SAMO kao referenca za ispravan
pristup (avatar pipeline, hide-when-empty). Ovdje je sve implementirano
FRESH u zasebnom worktree-u po reviziji — ne gradi se na Codex-ovom diff-u.

## Task Contract (revizija, aktivna specifikacija)

Izvor: `agent_reports/DENT-021-task-contract.md`, sekcija
"⚠ Revizija (21.8.2026)". Radovanove odluke:

1. Fotografije povećati (`DOCTOR_AVATAR_SIZE` 38 → **48px**).
2. Prazan kružić boje → **obojena kružna znaka sa bijelim podebljanim
   brojem** = broj termina tog doktora u trenutno prikazanom periodu
   (sedmica ili dan), nezavisno od aktivnog doctor-filter taba.
3. Osvježavanje na istim mjestima gdje se već zove `_update_status_legend()`.

Originalni kontrakt (panel sa fotografijama umjesto jednoredne legende,
hide-when-empty, poravnanje sa DashboardPanels) i dalje važi.

## Šta je urađeno

- `desktop/assets/doctors/{ljubo,zorka,ana}.png` — lokalni placeholder
  bitmape (boja doktora + inicijali), generisani offscreen kroz Qt.
- `main_window.py`:
  - `DOCTOR_PHOTO_FILES`, `DOCTOR_AVATAR_SIZE = 48`,
    `_circular_doctor_pixmap()` (kružni isječak fotografije).
  - `doctor_legend` pretvoren u vertikalni panel: naslov "Doktori" +
    redovi (avatar 48px + ime + brojčana znaka 24px).
  - `self._doctor_badge_labels: dict[int, QLabel]` — referenca po doktoru.
  - `_update_doctor_panel_counts()` — čita `visible_doctor_counts()` sa
    aktivnog view-a i postavlja tekst znaka.
  - poziv `_update_doctor_panel_counts()` na kraju `_update_status_legend()`.
- `week_view.py` / `day_view.py`: `visible_doctor_counts()` — broj
  vidljivih termina po doktoru u trenutnom periodu, NAMJERNO ignoriše
  `_filter_doctor_id` (WeekView), pa panel prikazuje SVE doktore.

## Changed files

- `desktop/assets/doctors/ljubo.png` (novi)
- `desktop/assets/doctors/zorka.png` (novi)
- `desktop/assets/doctors/ana.png` (novi)
- `desktop/views/main_window.py`
- `desktop/views/week_view.py`
- `desktop/views/day_view.py`
- `tests/test_gui/test_week_view.py`
- `tests/test_gui/test_day_view.py`
- `tests/test_gui/test_main_window.py`

## Testovi

- `test_week_view.py`: `visible_doctor_counts` nezavisno od `set_filter()`.
- `test_day_view.py`: `visible_doctor_counts` za dan.
- `test_main_window.py`: badge prikazuje broj nakon `create()`;
  osvježavanje pri navigaciji (`_move_week`); `DOCTOR_AVATAR_SIZE >= 48`;
  panel skriven kad store nema doktore (FakeStore).
- Regresija: postojeći testovi sadržaja/poravnanja/navigacije ostaju.

## Verifikacija (rezultati)

```text
git diff --check
→ PASS, exit 0

ruff check src/dentaland desktop backend tests
→ All checks passed, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 35 source files, exit 0

pytest tests/ -q
→ 264 passed, 11 warnings, exit 0
   (258 baseline + 1 week_view + 1 day_view + 4 main_window)
```

Offscreen smoke (1536×760, pravi AppointmentService):

```text
badges: {Ljubo(1): '1', Zorka(2): '1', Ana(3): '0'}
doctor_legend visible: True
avatar size: 48x48, pixmap: 48
```

Warnings su postojeći dependency deprecation warning-i (httpx/slowapi/alembic),
ne vezani za ovaj task.

## Review

`PENDING` — implementer nije reviewer. Claude radi nezavisan LOW-risk
review sa stvarnom reprodukcijom.

## Integration status

`NOT_MERGED` — čeka nezavisan review.

## Handoff

CILJ: panel doktora sa većim avatarima i brojčanom znakom po doktoru.

URAĐENO: asseti + panel + `visible_doctor_counts` + brojčana znaka +
testovi.

NE DIRATI: `src/dentaland/`, `migrations/`, Codex-ov necommitovan diff u
glavnom checkout-u (čisti se tek nakon merge-a).

SLJEDEĆE: Claude nezavisan review.
