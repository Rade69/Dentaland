---
task_id: DENT-IMPROVE-004
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-20
---

# DENT-IMPROVE-004 — Implementirati „Blokiraj vrijeme"

## Probni signal — `.agent/` navigacioni sloj (zabilježeno prije prve izmjene koda)

- **Fajlova pročitanih prije 1. izmjene koda: 11** read pozivom u ovom
  zadatku: `agent_reports/DENT-IMPROVE-004-task-contract.md`,
  `.agent/CURRENT_STATE.md`, `src/dentaland/models.py`,
  `src/dentaland/services/booking.py`, `desktop/views/week_view.py`,
  `desktop/views/dialogs/base_dialog.py`, `desktop/views/requests_panel.py`,
  `desktop/views/stub_page.py`, `tests/test_services.py`,
  `tests/test_gui/test_requests_panel.py`, `tests/test_gui/test_week_view.py`.
  Dodatno, iz prethodnih zadataka već su bili u kontekstu: `CLAUDE.md`,
  `.agent/PROJECT_MAP.md`, `.agent/TASK_ROUTING.md`,
  `docs/DENTALAND_IMPROVEMENT_BACKLOG.md` (sekcija 5),
  `docs/dentaland-agentski-razvoj.md`, `desktop/views/main_window.py`,
  `desktop/views/sidebar.py`.
- Koristio `.agent/PROJECT_MAP.md`: **DA** — "Booking domain" i "Desktop
  scheduler" sekcije su pokazale `booking.py`, `main_window.py`,
  `sidebar.py` i relevantne GUI testove.
- Koristio `.agent/TASK_ROUTING.md`: **DA** — kombinovao Booking/service
  routing (servisne metode + `test_services.py`) i Desktop GUI routing
  (panel + `tests/test_gui/`); nisam učitavao `backend/`/`web/`/`migrations/`.
- Tražio dodatno pojašnjenje strukture: **DA, ciljano** — grep za postojeće
  `time_off`/`blockout`/`TimeOff` reference u testovima (da ne dupliram
  postojeće pokriće `time_off_for_week` i prikaza blokade u WeekView),
  `git log main` + `coordination status`. Nije bilo repo-wide lutanja.
- Ostao u `allowed_paths`: **DA** — planirane izmjene su isključivo
  `src/dentaland/services/booking.py`, `desktop/views/blockout_panel.py`
  (novi), `desktop/views/main_window.py`, `tests/test_services.py`,
  `tests/test_gui/test_blockout_panel.py` (novi). `models.py`/`migrations/`
  nisu dirani (postojeći `TimeOff` model JE dovoljan — vidi niže).

## Task Contract

Izvor: `agent_reports/DENT-IMPROVE-004-task-contract.md` (puni detalj u
`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 5).

Cilj: korisnik trenutno nema UI da kreira/ukloni blokirano vrijeme
(`TimeOff` model i prikaz na kalendaru već postoje). Napraviti minimalan
workflow: doktor → datum → vrijeme od/do → razlog (opciono) → Sačuvaj,
plus prikaz aktivnih/nadolazećih blokada i brisanje uz potvrdu. MEDIUM
risk; jedan nezavisan reviewer (Claude).

**Allowed paths:** `src/dentaland/services/booking.py`, `desktop/views/`,
`tests/test_services.py`, `tests/test_gui/`. Model/migration se ne mijenja
osim ako se dokaže da `TimeOff` nije dovoljan.

## Zaključak o modelu — `TimeOff` je dovoljan

`src/dentaland/models.py` → `TimeOff(id, doctor_id, od_datetime,
do_datetime, razlog)` pokriva sve što workflow traži (doktor, od, do,
razlog opciono). **Nije potrebna nikakva izmjena `models.py`/`migrations/`.**

## Scope

- `src/dentaland/services/booking.py` — `TimeOffDTO` + `create_time_off()`,
  `list_time_off()`, `delete_time_off()` + overlap provjera blokada-vs-termin.
- `desktop/views/blockout_panel.py` — novi panel (forma + lista + brisanje
  uz potvrdu).
- `desktop/views/main_window.py` — ruta `blockout` umjesto `StubPage`
  prikazuje `BlockoutPanel`; `changed` → `_refresh_dashboard`.
- `tests/test_services.py` — testovi servisnih metoda.
- `tests/test_gui/test_blockout_panel.py` — GUI testovi panela.

Netaknuto: `models.py`, `migrations/`, `desktop/views/sidebar.py` (ruta
`blockout` već postoji u `Sidebar.QUICK`), postojeća logika prikaza blokada
u `week_view.py` (već pokrivena `test_blockout_je_spojen_i_ne_emituje_slobodan_slot`).

## Šta je urađeno

### Servisni sloj (`booking.py`)

- `TimeOffDTO(id, doctor_id, doctor_name, start, end, reason)` — plain
  DTO za GUI (isti princip kao `AppointmentDTO`).
- `create_time_off(doctor_id, start, end, reason=None)`:
  - odbija `end <= start` (`ValueError`),
  - odbija preklapanje sa `SCHEDULED` terminom istog doktora
    (`OverlapError` sa jasnom porukom) — postojeći termini se nikad ne
    obrišu/pomjere,
  - kreira `TimeOff` i vraća DTO.
- `list_time_off()` — aktivne i nadolazeće blokade (`do_datetime >= sada`),
  hronološki, sa `doctor_name`.
- `delete_time_off(time_off_id)` — trajno uklanja; nepoznat id →
  `ValueError`.

### UI (`blockout_panel.py`)

- Forma: doktor (combo), datum (date edit), od/do (time edit), razlog
  (opciono), "Sačuvaj".
- Inline greška: `end <= start` se provjerava prije poziva servisa; servisne
  greške (`OverlapError`/`ValueError`) se prikazuju inline.
- Lista "Aktivne blokade" sa dugmetom "Obriši" — brisanje ide kroz
  `QMessageBox.question` potvrdu (Yes/No).
- `changed` signal nakon svake uspješne izmjene → `main_window` osvježi
  kalendar (blokada se odmah vidi na rasporedu).

## Tehničke odluke

### Overlap provjera je nova metoda, ne izmjena `_check_overlap`

Postojeća `_check_overlap` je za termine i njena poruka ("termin se
preklapa...") je netačna u kontekstu blokade. Dodata je
`_check_timeoff_overlap` sa porukom specifičnom za blokadu — nula rizika za
postojeće pozivaoce `_check_overlap`.

### Jedan dan po blokadi

Backlog user flow je "doktor → datum → vrijeme od/do" — jedan datum. Model
podržava višednevne blokade (proizvoljni `od_datetime`/`do_datetime`), ali
UI namjerno ostaje minimalan (jedan dan). Višednevno je moguć follow-up,
ne dio ovog taska.

### Sidebar se ne dira

`Sidebar.QUICK` već sadrži `("blockout", "Blokiraj vrijeme", "clock")` i
emituje rutu `blockout` — samo je u `main_window.py` zamijenjen `StubPage`
pravim panelom.

## Verifikacija (rezultati)

```text
git diff --check
→ PASS, exit 0

ruff check src/dentaland desktop backend tests
→ All checks passed, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 33 source files, exit 0

pytest tests/ -q
→ 240 passed, 11 warnings, exit 0
   (229 baseline + 7 servisnih time_off testova + 4 GUI blockout testa)
```

Ručni/offscreen smoke (bez otvaranja stvarne baze u GUI):

```text
servis (SQLite tmp): create_time_off -> list_time_off -> delete_time_off
→ create: Ljubo 'smoke'; list: [(1, 'Ljubo')]; after delete: []
GUI (offscreen): MainWindow(FakeStore()) — _route_pages['blockout']
→ BlockoutPanel
```

Warnings su postojeći dependency deprecation warning-i (httpx/slowapi/alembic),
ne vezani za ovaj task.

## Review

`PENDING` — implementer nije reviewer. Potreban je nezavisan Claude review
sa fokusom na scope, acceptance (posebno: end<=start, overlap upozorenje,
izolacija po doktoru) i UX brisanja uz potvrdu.

## Integration status

`NOT_MERGED` — čeka nezavisan review i Radovanov human approval (MEDIUM).

## Handoff

CILJ: operativni UI za kreiranje/prikaz/brisanje blokiranog vremena.

URAĐENO: servisne metode + panel + navigacija + testovi; kalendar već
prikazuje blokade (postojeći `time_off_for_week`/WeekView).

NE DIRATI: `models.py`/`migrations/`, postojeću overlap logiku termina.

SLJEDEĆE: Claude radi nezavisan MEDIUM-risk review; nakon PASS-a Radovanov
human approval, pa merge.
