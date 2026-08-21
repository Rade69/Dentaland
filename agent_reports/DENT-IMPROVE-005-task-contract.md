---
task_id: DENT-IMPROVE-005
risk: MEDIUM
implementer: crush
reviewers: [claude]
verdict: PASS_WITH_NOTES
status: MERGED_INTEGRATION_VERIFIED
commits: [a0c7ef4]
created_at: 2026-08-20
---

## Integration status

`MERGED → INTEGRATION_VERIFIED → DONE` (21.8.2026). Review: Claude
`PASS_WITH_NOTES` (`agent_reports/2026-08-21-DENT-IMPROVE-005-review-claude.md`)
— adversarno testirani touching-boundary, prazna-lista i
po-danu-izolacija slučajevi, svi prošli. Human approval: Radovan
("komituj i merdžuj"). Merge commit na `main` (`--no-ff`). Post-merge
gate: `pytest` → 251 passed, `ruff` → All checks passed, `mypy` → 0
grešaka (34 fajlova). Dvije manje napomene (GUI test coverage na Radno
vrijeme tabu; `doctors()`/`list_doctors()` asimetrija — deaktiviran
doktor nestaje iz Radno vrijeme combo-a, podaci ostaju u bazi) nisu
blocking.

# DENT-IMPROVE-005 — Minimalne Postavke

## Task Contract

**Cilj:** Doktori, usluge i radno vrijeme postoje u modelu, ali se
aplikacija praktično oslanja na seed podatke. Napraviti samo minimalne
postavke koje ordinacija stvarno treba: doktori (lista, aktivan/neaktivan),
usluge (naziv, trajanje, buffer, dodavanje/uređivanje), radno vrijeme
(doktor, dan u sedmici, jedan ili više intervala od/do — split shift).

**Risk:** MEDIUM

**Izvor:** `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 6
(`DENT-IMPROVE-005`) — pun detalj tamo, ali prvo pokušaj sam kroz
`AGENTS.md`/`CLAUDE.md` → `.agent/PROJECT_MAP.md`/`.agent/TASK_ROUTING.md`
odrediti šta ti treba; backlog koristi tek ako ti nešto ostane nejasno.

**Explicitly out of scope:** korisnički nalozi, RBAC, SMTP settings UI,
cloud settings, multi-tenancy, branding editor.

**Architecture rule:** Business/database operacije ostaju u servisnom
sloju. `desktop/views/` ne uvozi SQLAlchemy direktno.

**Acceptance:**
- aktivacija/deaktivacija doktora radi bez brisanja istorije,
- promjena trajanja usluge utiče na nove termine,
- radno vrijeme podržava split shift,
- validacija sprečava nelogične intervale,
- postojeći scheduler nastavlja raditi.

**Verification:** service tests, GUI tests, existing scheduling regression
tests, full gate.

**Review:** Claude, nezavisan od implementera.

## Koordinacija — obavezno prije početka

Bolje raditi NAKON `DENT-IMPROVE-004` (oba diraju navigaciju i dio
servisnog sloja — backlog eksplicitna napomena). Provjeri
`scripts/coordination.py status` prije `claim`.

## Probni signal — obavezno u `agent_report`

Prije prve izmjene, kratko zapiši: koliko fajlova si pročitao prije prve
izmjene, da li si koristio `.agent/PROJECT_MAP.md`/`.agent/TASK_ROUTING.md`,
da li si tražio dodatno pojašnjenje strukture, da li si ostao u
`allowed_paths`. Nastavak mjerenja iz
`agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md`.
