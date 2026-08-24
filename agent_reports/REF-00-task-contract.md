---
task_id: REF-00
risk: LOW/MEDIUM
implementer: pi
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit ce8d65a, 2026-08-24), post-merge integration gate PASS (317 pytest, ruff, mypy)."
created_at: 2026-08-24
merged_at: 2026-08-24
---

# REF-00 — Arhitektonska sigurnosna mreža (characterization testovi)

## Task Contract

**Cilj:** Zaključati trenutno ponašanje aplikacije prije nego što REF-01..08
počnu premještati hotspot fajlove (`main_window.py`, `booking.py`). Ovo je
JEDINA sigurnosna mreža za sedam narednih taskova — ne žuri se zbog niskog
risk tier-a.

**Risk:** LOW/MEDIUM (dodaje SAMO testove i dokumentaciju; ne dira
produkcijski kod).

Izvor: `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`, sekcija 7
(+ napomena 24.8.2026 ispod naslova REF-00).

## Allowed paths

```text
tests/**
agent_reports/**
docs/**
```

## Forbidden paths

```text
desktop/**
src/dentaland/**
backend/**
migrations/**
```

## Zadaci

1. **Characterization test lista/mapa** — `docs/dentaland-ref00-characterization-map.md`:
   mapirati ključna ponašanja (create appointment, edit, move, cancel,
   delete, status transitions, web request confirm/reject, Day/Week switch,
   doctor filter, TimeOff/block rendering, print action, status summary) na
   POSTOJEĆE testove, i označiti koja ponašanja su već pokrivena, a koja
   nedostaju.
2. **Identifikovati mjesta gdje trenutni testovi testiraju implementacijski
   detalj umjesto contracta** — zabilježiti u mapi (ne mijenjati te testove
   u ovom tasku).
3. **Dodati SAMO nedostajuće testove** (novi fajlovi, ne prepravljati
   postojeće):
   - `tests/test_ref00_overlap_error_contract.py` — baseline test za DVIJE
     odvojene `OverlapError` klase (vidi "Dodatni zadatak").
   - `tests/test_ref00_service_api_contract.py` — javni API surface
     `AppointmentService` + DTO polja + re-eksporti iz
     `dentaland.services` (zaključava samo JAVNE simbole, ne privatne).
4. **GUI testovi i geometrija** — ne dodavati nove testove koji zavise od
   `width()/sizeHint()`; ako je potrebno, koristiti deterministički
   sadržaj/state provjere (presedan FIX-03: geometrijsko poređenje daje
   lažan PASS).

## Dodatni zadatak (iz review-a 24.8.2026)

Napraviti test koji eksplicitno bilježi koju `OverlapError` klasu danas
hvata desktop poziv (preko `dentaland.services`) i koju backend API poziv
(`backend/main.py`):

- `booking.OverlapError` (`src/dentaland/services/booking.py:135`) — re-eksport
  kroz `dentaland.services`, hvataju je `desktop/views/main_window.py`,
  `day_view.py`, `week_view.py`, `blockout_panel.py`.
- `requests.OverlapError` (`src/dentaland/services/requests.py:30`) — hvataju
  je `backend/main.py:172` i `desktop/views/requests_panel.py`.

Ovo postaje baseline koji REF-01 mora svjesno zadržati ili promijeniti, ne
slučajno slomiti.

## Acceptance

- [ ] full baseline prolazi (298 pytest, ruff čist, mypy čist);
- [ ] postoji mapa ključnih ponašanja → testovi;
- [ ] nema produkcijskog koda dirnutog;
- [ ] reviewer može jasno vidjeti koji test štiti koji workflow;
- [ ] test za dvije `OverlapError` klase postoji i dokumentuje trenutno stanje.

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline (24.8.2026, `main` nakon DENT-IMPROVE-009): 298 pytest passed,
ruff/mypy čisti. Provjeriti tačan broj na svom worktree-u prije početka.

## Review

Codex I Claude — OBA obavezna (cijeli REF paket, dogovoreno sa Radovanom).
Codex: test kvalitet (da li novi test zaista pada kad se invariant pokvari).
Claude: da testovi ne zaključavaju lošu arhitekturu/privatne detalje.
Redoslijed: Codex prvi.

**STOP. Merge tek poslije Radovan human approval-a, i tek nakon oba
reviewera.**

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim`. Radi u
zasebnom git worktree (`Dentaland-worktrees/REF-00-characterization-tests`,
grana `task/REF-00-characterization-tests`).
