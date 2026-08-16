---
task_id: DENT-001
risk: HIGH
implementer: crush
reviewers: [claude, codex]
verdict: PASS_WITH_NOTES
commits: []
created_at: 2026-08-16
---

# DENT-001 — SQLAlchemy modeli i initial Alembic migracija

## Task Contract

```yaml
id: DENT-001
title: Faza 0 — SQLAlchemy modeli i initial Alembic migracija (osnovna šema)
risk: HIGH
allowed_paths: [pyproject.toml, src/dentaland/**, migrations/**, alembic.ini,
  tests/test_models.py, agent_reports/**]
forbidden_paths: [CLAUDE.md, AGENTS.md, docs/**, desktop/**]
```

Pun tekst contracta je u `paste_1.txt` (priložen uz zadatak).

## Šta je urađeno

- `src/dentaland/models.py` — `Base` (DeclarativeBase), enum `AppointmentStatus`
  (`enum.StrEnum`: SCHEDULED/CANCELLED/COMPLETED/NO_SHOW), `TZDateTime`
  TypeDecorator (odbacuje naivan datetime, normalizuje na UTC), i pet modela:
  `Doctor`, `Service`, `WorkingHours`, `TimeOff`, `Appointment` sa FK
  relacijama (working_hours/time_off/appointments → doctors; appointments →
  services).
- `src/dentaland/__init__.py` — re-export javnih simbola.
- `alembic.ini` + `migrations/env.py` + `migrations/script.py.mako` +
  `migrations/versions/a1b2c3d4e5f6_initial_schema.py` — initial migracija
  (create/drop pet tabela) koja se oslanja na `Base.metadata`.
- `tests/test_models.py` — 13 testova (kreiranje tabela, FK relacije,
  timezone-aware provjera, validacija statusa, default vrijednosti).
- `pyproject.toml` — dodane zavisnosti SQLAlchemy/Alembic/tzdata i
  `[tool.pytest.ini_options] pythonpath = ["src"]`.
- `agent_reports/2026-08-16-DENT-001-plan.md` — plan prije izmjene (HIGH).

## Verifikacija (stvarni rezultati)

| Komanda | Rezultat |
|---|---|
| `python -m pytest tests/test_models.py -v` | 13 passed |
| `python -m ruff check src/dentaland tests/test_models.py` | All checks passed |
| `python -m alembic upgrade head` | Running upgrade → a1b2c3d4e5f6 (OK) |
| `python -m alembic downgrade base` | Running downgrade a1b2c3d4e5f6 → (OK) |

## Odbačene opcije

- Enum kao prost `String` + aplikacijska provjera — odbačeno: acceptance traži
  pravi enum; `Enum(..., native_enum=False, validate_strings=True)` daje i
  CHECK constraint i ORM validaciju.
- `DateTime(timezone=True)` bez TypeDecorator-a — odbačeno: ne odbacuje naivan
  datetime; `TZDateTime` koncentriše pravilo na jednom mjestu.
- `od_local`/`do_local` kao `DateTime` — odbačeno: to su rekurentna vremena uz
  `dan_u_sedmici` i `timezone`; `Time` je tačniji tip.

## Review

Codex prvi review: REJECT — pronađeno da SQLite enum nema DB CHECK constraint,
da `is_manual_override` nema DB default i da testovi ne izvršavaju Alembic
migraciju.

## Popravke poslije Codex reviewa

- `Appointment.status` sada koristi `create_constraint=True` i u modelu i u
  initial migraciji, pa SQLite fizički odbacuje status van definisanog enuma.
- `is_manual_override` sada ima `server_default=false` uz postojeći Python
  default.
- Dodat je Alembic integration test koji radi `upgrade head`, introspektuje
  CHECK/default, radi `downgrade base` i potvrđuje da su tabele uklonjene.
- Initial migracija je usklađena sa Ruff pravilima za Python 3.12.

Verdict ostaje PENDING do ponovljene automatske verifikacije i nezavisnih
reviewera. Procesni nalaz da je HIGH zadatak implementirao Crush mora odobriti
Radovan ili se zadatak mora vratiti toku definisanom u važećem `CLAUDE.md`.

## Verifikacija poslije popravki (Codex, 2026-08-16)

| Komanda | Rezultat |
|---|---|
| `python -m pytest tests/test_models.py -v` | 14 passed |
| `python -m ruff check src/dentaland tests/test_models.py migrations` | All checks passed |
| `python -m mypy src/dentaland` | Success |
| `git diff --check` | PASS |

Pytest prikazuje dvije Alembic deprecation napomene za nedostajući
`path_separator` u `alembic.ini`; ne utiču na ispravnost migracije i mogu se
riješiti zasebnom konfiguracijskom izmjenom.

## Claude review (Reviewer 1, 16.8.2026)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisno pročitan `models.py`, initial migracija, `test_models.py`, `env.py`, i diff `pyproject.toml`. Nezavisno ponovo pokrenuto (ne oslanjajući se na brojeve iz izvještaja):

| Komanda | Rezultat |
|---|---|
| `pytest tests/test_models.py -v` | 14 passed |
| `ruff check src/dentaland tests/test_models.py migrations` | All checks passed |
| `alembic upgrade head` / `downgrade base` | Oba prošla |

Svih sedam acceptance stavki iz Task Contracta potvrđeno: kolone tačno prema v3.1 planu, `status` je pravi enum sa CHECK constraintom (i u modelu i u migraciji), `is_manual_override` ima i Python i DB default, `TZDateTime` odbacuje naivan datetime (testabilno, testovi pokrivaju i pozitivan i negativan slučaj), Alembic upgrade/downgrade rade na praznoj bazi, FK relacije testirane za sve tri zavisne tabele, ruff čist. Scope čist — dirani su samo `allowed_paths`, ništa iz `forbidden_paths` (CLAUDE.md/AGENTS.md/docs/desktop) nije dirano.

**Napomene (ne blokiraju, LOW):**
- `doctors.aktivan` ima Python-side default (`default=True`) ali nema `server_default` u migraciji — nekonzistentno sa `is_manual_override`, koji je dobio oba nakon prvog Codex nalaza. Sitan gap: direktan insert mimo ORM-a (raw SQL/seed skripta) bi zahtijevao eksplicitnu vrijednost. Ne blokira jer sav Faza 0 pristup ide kroz ORM.
- `working_hours.dan_u_sedmici` je prost `Integer` bez CHECK constrainta na opseg 1–7 (ISO dan u sedmici, dokumentovano samo komentarom). Isti obrazac kao `status` (CHECK constraint) bi ovo učinio fizički nemogućim umjesto samo konvencijom. Nisko-rizično za Fazu 0 (jedan pouzdan unosilac po worktree-u), ali vrijedno OUT_OF_SCOPE_FINDING zapisa za budući hardening zadatak.

Verdikt: **PASS_WITH_NOTES**. Oba reviewera (Claude, Codex) su nezavisno završila — spremno za human approval.

## Integration status

MERGED → INTEGRATION_VERIFIED → DONE. Implementacija je odobrena kao izuzetak od procesa (implementer je Crush umjesto Claude, zbog role promjene koja je stigla nakon što je zadatak već bio u toku) — odobreno 16.8.2026. Mergovano u `main` (commit `414359a`) uz DENT-002 (`8c23c71`). Post-merge integration gate pokrenut zajedno sa DENT-002: pun test suite (23/23, uključujući GUI testove), `ruff check` na cijelom repou, `alembic upgrade`/`downgrade` smoke test — svi prošli. Ažurirano 16.8.2026 (ranije je fajl pogrešno stajao na `NOT_MERGED` i poslije stvarnog merge-a — evidence dokumentacija nije ažurirana u trenutku merge-a, propust uočen kroz nezavisnu analizu koda).
