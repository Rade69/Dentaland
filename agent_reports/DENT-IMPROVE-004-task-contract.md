---
task_id: DENT-IMPROVE-004
risk: MEDIUM
implementer: TBD
reviewers: [claude]
created_at: 2026-08-20
---

# DENT-IMPROVE-004 — Implementirati „Blokiraj vrijeme"

## Task Contract

**Cilj:** Model i servis već imaju `TimeOff`, kalendar ga može prikazati,
ali korisnik nema UI da kreira ili ukloni blokirano vrijeme. Napraviti
minimalan operativni workflow za odsustvo/blokadu (doktor, datum, vrijeme
od/do, razlog opciono; prikaz aktivnih/nadolazećih blokada; brisanje uz
potvrdu).

**Risk:** MEDIUM

**Izvor:** `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 5
(`DENT-IMPROVE-004`) — pun detalj tamo (user flow, suggested service
metode), ali prvo pokušaj sam kroz `AGENTS.md`/`CLAUDE.md` →
`.agent/PROJECT_MAP.md`/`.agent/TASK_ROUTING.md` odrediti šta ti treba;
backlog koristi tek ako ti nešto ostane nejasno.

**Allowed paths:** `src/dentaland/services/booking.py`, `desktop/views/`,
`tests/test_services.py`, `tests/test_gui/`. Model/migration se ne
mijenja osim ako dokažeš da postojeći `TimeOff` model nije dovoljan —
ako se to desi, stani i prijavi prije nego dirneš `models.py`.

**Acceptance:**
- može se kreirati blokada,
- prikazuje se na kalendaru,
- ne može se unijeti `end <= start`,
- može se obrisati,
- blokada drugog doktora ne utiče na pogrešnog doktora,
- postojeći termini nisu tiho obrisani/pomjereni,
- ako blokada preklapa postojeći termin, aplikacija eksplicitno upozorava
  korisnika.

**Verification:** service tests, GUI tests, ručni smoke test, full
`pytest`/`ruff`/`mypy`.

**Review:** Claude, nezavisan od implementera.

## Koordinacija — obavezno prije početka

Ovaj task dira `desktop/views/` (uklj. `main_window.py`/`sidebar.py` po
potrebi navigacije) — pokreni tek nakon što je `DENT-IMPROVE-003`
MERGED, provjeri `scripts/coordination.py status` prije `claim`.

## Probni signal — obavezno u `agent_report`

Prije prve izmjene, kratko zapiši: koliko fajlova si pročitao prije prve
izmjene, da li si koristio `.agent/PROJECT_MAP.md`/`.agent/TASK_ROUTING.md`,
da li si tražio dodatno pojašnjenje strukture, da li si ostao u
`allowed_paths`. Nastavak mjerenja iz
`agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md`.
