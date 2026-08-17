---
task_id: DENT-012
risk: HIGH
implementer: claude
reviewers: [codex, crush]
status: READY_FOR_REVIEW
commits: []
created_at: 2026-08-17
---

# Evidence — DENT-012: confirmed_at / arrived_at

## Task Contract

Vidi `agent_reports/2026-08-17-DENT-012-plan.md` za pun plan, uključujući
odbačenu alternativu (proširenje `AppointmentStatus` enuma) i korekciju
obima (uklonjen `booking.py`/`AppointmentDTO` — nema GUI koda koji bi
polja koristio u ovom trenutku).

```yaml
id: DENT-012
title: Appointment.confirmed_at / arrived_at — podloga za buduće status ikonice
risk: HIGH
objective: >
  Dodati dvije nullable timestamp kolone (confirmed_at, arrived_at) na
  Appointment, nezavisne od AppointmentStatus enuma, kao podlogu za
  buduću GUI dopunu (status ikonice na terminima, iz
  docs/istrazivanje-dentalni-scheduler-gui.md). Bez UI koda u ovom
  zadatku — čista šema.
allowed_paths: [src/dentaland/models.py, migrations, tests/test_models.py, tests/test_requests.py, agent_reports/**]
forbidden_paths: [desktop/, backend/, web/, src/dentaland/services/booking.py, src/dentaland/services/requests.py, CLAUDE.md, AGENTS.md]
acceptance:
  - confirmed_at i arrived_at su nullable TZDateTime kolone na Appointment.
  - AppointmentStatus enum se ne mijenja.
  - requests.py (confirm_request) se ne dira u ovom zadatku — popunjavanje pri potvrdi je poseban follow-up.
  - Alembic migracija (batch mode) dodaje kolone, downgrade ih uklanja bez gubitka ostalih podataka.
  - Postojeći redovi poslije migracije imaju NULL u oba nova polja (nema server_default).
verification: [pytest tests/ -q, ruff check src/dentaland tests migrations, mypy src/dentaland desktop (baseline provjera), nezavisna alembic upgrade/downgrade provjera]
review:
  reviewers: 2
  required: [security, architecture, scope]
```

## Šta je urađeno

- `src/dentaland/models.py`: `Appointment.confirmed_at`, `Appointment.arrived_at`
  — oba `Mapped[datetime | None]` preko `TZDateTime()`, sa docstring
  komentarom koji objašnjava da su nezavisni od `status` (termin može
  biti SCHEDULED + potvrđen + još-nije-stigao istovremeno).
- `migrations/versions/c3d4e5f6a7b8_confirmed_arrived.py`: batch-mode
  migracija (`recreate="always"`), nadovezuje se na `b2c3d4e5f6a7`
  (DENT-007, jedini head prije ovog zadatka). `add_column` x2 u
  `upgrade()`, `drop_column` x2 (obrnutim redoslijedom) u `downgrade()`.
  Bez `server_default` — postojeći redovi dobijaju NULL.
- `tests/test_models.py`: četiri nova testa —
  `test_confirmed_arrived_at_default_none`,
  `test_confirmed_arrived_at_prihvataju_aware_datetime`,
  `test_alembic_migracija_dodaje_confirmed_arrived_at` (upgrade na
  praznu privremenu bazu, provjera kolona, downgrade na `base`, provjera
  da ostaje samo `alembic_version`),
  `test_migracija_cuva_postojece_termine_pri_upgrade_i_downgrade`
  (dodano poslije Codex review-a, vidi "Review" ispod — upgrade SAMO do
  `b2c3d4e5f6a7`, upis stvarnog termina raw SQL-om, upgrade na `head` uz
  provjeru da postojeći red dobija NULL u oba nova polja, downgrade nazad
  na `b2c3d4e5f6a7` uz provjeru da termin i status nisu izgubljeni).

Namjerno NE urađeno (van obima, dokumentovano u planu):
- `AppointmentDTO`/`booking.py` — nema polja dok ne postoji GUI kod koji
  ih koristi.
- `confirm_request()` u `requests.py` ne popunjava `confirmed_at` —
  poseban uzan follow-up kad zatreba (jedan red u već testiranoj
  funkciji, izvan `allowed_paths` ovog zadatka).
- Nema izmjene `EXCLUDE`/overlap-check logike — i dalje filtrira
  isključivo po `status`.

## Verifikacija

```
pytest tests/ -q
74 passed, 11 warnings in 4.86s

ruff check src/dentaland tests migrations
All checks passed!

mypy src/dentaland desktop
Found 8 errors in 3 files (checked 13 source files)
— identično poznatoj baseline u desktop/ (appointment_dialog.py,
  week_view.py x4, main_window.py x2), nula novih grešaka iz ove izmjene.
```

Nezavisna alembic provjera (van test suite-a, direktan Python poziv):
upgrade na privremenu bazu → `confirmed_at`/`arrived_at` prisutni i
nullable → downgrade na `base` → preostaje samo `alembic_version`.
Potvrđeno, izlaz priložen u sesiji.

## Review

**Codex (Reviewer 1) — PASS_WITH_NOTES → primijenjeno, sad PASS.**

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Codex-ov ključni nalaz: `test_alembic_migracija_dodaje_confirmed_arrived_at`
pokreće migraciju na PRAZNOJ bazi — ne dokazuje eksplicitne acceptance
stavke "postojeći termini poslije upgrade-a dobijaju NULL" i "downgrade
ne gubi postojeće termine". Codex je nezavisno ručno provjerio migraciju
na privremenoj bazi sa stvarnim terminom i potvrdio da radi ispravno, ali
je tražio da HIGH-risk acceptance bude pokriven determinističkim
testom, ne samo ručnom provjerom — ispravno pozivanje na hijerarhiju
dokaza iz CLAUDE.md (test > ručna provjera). Dodan
`test_migracija_cuva_postojece_termine_pri_upgrade_i_downgrade` tačno
po Codex-ovim koracima (upgrade do `b2c3d4e5f6a7` → upis termina →
upgrade na `head` → provjera NULL → downgrade → provjera da termin
nije izgubljen). Prolazi.

Dvije procesne napomene, obje ispravljene:
- Coordination claim je navodio `agent_reports/DENT-012-task-contract.md`
  koji nikad nije kreiran (ugovor je od početka bio ugrađen u plan/evidence
  fajlove, ne poseban fajl) — claim ponovo izdat bez tog fantomskog puta.
- Plan fajl (`2026-08-17-DENT-012-plan.md`) je imao status `PLAN` i
  rečenicu koja je opisivala `confirmed_at` kao "popunjen odmah pri
  kreiranju" za ručni unos — u sudaru sa konačnom odlukom da ovaj zadatak
  isporučuje isključivo šemu, bez ikakvog popunjavanja. Tekst usklađen,
  status ažuriran na `IMPLEMENTED`.

GitNexus (Codex-ov nalaz): LOW blast radius, tri direktna zavisnika
modela, bez pogođenih izvršnih tokova — u skladu sa namjerno uskim
obimom ovog zadatka (šema bez GUI/servisne integracije).

**Pi (Reviewer 2) — REJECT → primijenjeno, sad PASS.** Pun review u
`agent_reports/2026-08-17-DENT-012-review-pi.md`. Jedini nalaz (scope,
jedini blokator): GitNexus alat je, dok je Codex radio Reviewer 1 pregled
sa `gitnexus_impact` u ovom worktree-u, kao nuspojavu ostavio
necommitovan GitNexus "Code Intelligence" blok u `CLAUDE.md` i
`AGENTS.md` (oba eksplicitno u `forbidden_paths` ovog HIGH-risk
zadatka) i `.claude/skills/gitnexus/` folder van `allowed_paths`. Pi je
ispravno insistirao da se to ne provuče kroz merge kao nuspojava
nevezanog alata, bez obzira na to što je sadržaj sam po sebi bezopasan.

Ispravljeno: `git restore CLAUDE.md AGENTS.md`, obrisan
`.claude/skills/gitnexus/`. Worktree je sad čist (samo fajlovi iz
`allowed_paths`). Acceptance/architecture/security su bez primjedbi na
oba reviewa (Codex i Pi), uključujući nezavisno pokrenut migracioni
test za očuvanje podataka (ne samo pročitan da postoji).

GitNexus integracija (ako se pokaže korisna) ostaje otvoreno pitanje za
poseban, namjeran zadatak — ne nešto što se tiho uvuče kroz šema PR.

## Integration status

`READY_FOR_REVIEW → REVIEWED (Codex PASS, Pi PASS poslije scope
ispravke)` — čeka human approval (Radovan) prije merge-a.
