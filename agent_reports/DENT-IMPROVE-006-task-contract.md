---
task_id: DENT-IMPROVE-006
risk: LOW/MEDIUM
implementer: TBD
reviewers: [claude]
created_at: 2026-08-20
---

# DENT-IMPROVE-006 — Pretvoriti „Novi zahtjevi" u pravi ekran

## Task Contract

**Cilj:** Sidebar ima rutu „Novi zahtjevi", ali vodi na `StubPage("Uskoro")`.
Stvarna obrada zahtjeva već postoji kroz `DashboardPanels`. Iskoristiti
postojeću logiku i napraviti dedicated requests page (ime, telefon/email po
potrebi, traženi datum, vrijeme kreiranja, dugme "Obradi" koje koristi
postojeći `ProcessRequestDialog`).

**Risk:** LOW/MEDIUM

**Izvor:** `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 7
(`DENT-IMPROVE-006`) — pun detalj tamo, ali prvo pokušaj sam kroz
`AGENTS.md`/`CLAUDE.md` → `.agent/PROJECT_MAP.md`/`.agent/TASK_ROUTING.md`
odrediti šta ti treba; backlog koristi tek ako ti nešto ostane nejasno.

**Important rule:** Ne duplirati business logiku iz `DashboardPanels`.

**Out of scope:** istorija svih zahtjeva, CRM, patient profile, analytics.

**Acceptance:**
- sidebar route više nije stub,
- pending count se podudara sa servisom,
- confirm/reject radi,
- nakon obrade lista se osvježi,
- postojeći dashboard panel ne gubi funkcionalnost.

**Verification:** GUI tests, ručni smoke test, full
`pytest`/`ruff`/`mypy`.

**Review:** Claude, nezavisan od implementera.

## Koordinacija — obavezno prije početka

Dira sidebar rutu (`main_window.py`/`sidebar.py`) — pokreni tek nakon što
je `DENT-IMPROVE-003` MERGED; preporučeno i nakon `004`/`005` da se
izbjegnu konflikti na istim navigacionim fajlovima. Provjeri
`scripts/coordination.py status` prije `claim`.

## Probni signal — obavezno u `agent_report`

Prije prve izmjene, kratko zapiši: koliko fajlova si pročitao prije prve
izmjene, da li si koristio `.agent/PROJECT_MAP.md`/`.agent/TASK_ROUTING.md`,
da li si tražio dodatno pojašnjenje strukture, da li si ostao u
`allowed_paths`. Nastavak mjerenja iz
`agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md`.
