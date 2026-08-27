---
task_id: DENT-IMPROVE-014
risk: HIGH
implementer: claude
reviewers: [codex, pi]
status: "IMPLEMENTED — čeka review (dva nezavisna reviewera, v3.1 princip #7)"
created_at: 2026-08-27
---

# Izvještaj — DENT-IMPROVE-014: Append-only audit log (jezgro)

## Šta je urađeno

1. `src/dentaland/models.py` — dodani `AuditAction` (enum, tačno 7 backlog
   "Minimum events" vrijednosti: `LOGIN_SUCCESS`, `LOGIN_FAILURE`,
   `CREATE_APPOINTMENT`, `UPDATE_APPOINTMENT`, `CANCEL_APPOINTMENT`,
   `DELETE_APPOINTMENT`, `CHANGE_ROLE`) i `AuditEvent` model — tačno 9
   polja iz v3.1 (linija 267-277): `id, actor_user_id, action,
   resource_type, resource_id, occurred_at, request_id, source_ip,
   metadata_minimal`. `actor_user_id` nullable FK → `users.id`.
   `Appointment`/`User`/`Session` netaknuti.
2. `src/dentaland/services/audit.py` (novo) — `write_audit_event(...)`.
   Vidi "API dizajn" ispod, najvažniji dio ovog izvještaja.
3. `migrations/versions/f6a7b8c9d0e1_audit_events.py` (novo,
   `down_revision=e5f6a7b8c9d0`, potvrđen head prije pisanja). Ručno
   provjereno: `upgrade head` → `audit_events` tabela sa tačno 9 kolona;
   `downgrade -1` → tabela čisto uklonjena, ostale tabele netaknute.
4. `tests/test_audit.py` (novo, 14 testova) — upis sa svim poljima, sva
   nullable polja rade, svih 7 akcija upisive, append-only ponašanje
   (uzastopni pozivi ne mijenjaju prethodne redove), `session=` parametar
   ne commit-uje (vidljivost izolovana dok pozivalac ne commit-uje) i
   rollback scenario (atomičnost), `metadata` se ne validira/sanitizuje
   (dokumentovano ponašanje), i eksplicitna provjera da servisni sloj
   nema `update`/`delete` funkciju.
5. **Nužna posljedica van originalnog allowed_paths popisa**:
   `tests/test_models.py::test_sve_tabele_su_kreirane` je imao egzaktnu
   `assert table_names == {...}` provjeru bez `audit_events` — dodao sam
   `"audit_events"` u očekivani set (jedna linija + komentar), isti obrazac
   kao `test_backend.py` izmjena u DENT-IMPROVE-013 planu ("nužna
   posljedica, ne proširenje obima").

## API dizajn — `write_audit_event(session_factory, action, *, ..., session=None)`

**Ovo je najvažnija stvar za 014C**: funkcija prihvata obavezan
`session_factory` (za samostalnu upotrebu) I opcioni keyword-only
`session: OrmSession | None = None`.

- `session` prosljeđen → `session.add(...)`, **BEZ `commit()`** — pozivalac
  (014C) upisuje audit red UNUTAR svoje postojeće `with session_factory()
  as session:` transakcije, oko izmjene termina. Ili oboje commit-uje
  zajedno, ili rollback poništi oboje. Provjereno testom
  (`test_write_audit_event_sa_postojecom_sesijom_ne_commituje` — red nije
  vidljiv iz druge sesije prije commit-a pozivaoca;
  `test_write_audit_event_sa_postojecom_sesijom_rollback_ne_upisuje` —
  rollback pozivaoca poništava i audit upis).
- `session` NIJE prosljeđen → funkcija otvara `with session_factory() as
  new_session:`, radi `add()` + `commit()` sama — pokriva 014B slučaj
  (login audit poziv u route handleru, bez okolne transakcije u tom
  smislu).

**Zaključak za 014C**: dizajn JE spreman za atomsku upotrebu koju 014C
zahtijeva, bez potrebe za dodatnim krugom na jezgru. 014C treba samo
pozvati `write_audit_event(session_factory, AuditAction.X, ...,
session=session)` unutar svoje postojeće `with session_factory() as
session:` bloka u `appointments.py`, prije (ili poslije, redoslijed
`session.add()` poziva unutar iste transakcije nije bitan) svog
`session.commit()` — jedan zajednički `commit()` pokriva oboje.

Odbačene alternative (dokumentovano u
`agent_reports/2026-08-27-DENT-IMPROVE-014-plan.md`): privatni
`_write_audit_event_in_session` helper (odbačeno — 014C je cross-modul
pozivalac, ne treba pozivati "privatnu" funkciju drugog modula); uvijek
zahtijevati postojeću sesiju (odbačeno — nepotrebno opterećenje za 014B
samostalni slučaj); DB-nivo trigeri za append-only (odbačeno —
neproporcionalno veličini projekta).

## Append-only odluka

Servisni sloj namjerno NE izlaže `update_audit_event`/`delete_audit_event`
niti bilo koju drugu mutacionu funkciju — dokumentovano eksplicitno u
docstringu `audit.py` i `AuditEvent` modela. Nema DB-nivo trigera/permisije
(direktan SQL UPDATE/DELETE je i dalje tehnički moguć) — proporcionalno
obimu projekta (CLAUDE.md "Šta se namjerno ne gradi unaprijed"). Test
`test_servisni_sloj_nema_update_delete_funkciju_za_audit` provjerava da
nijedno javno ime u modulu ne sadrži "update"/"delete".

## Acceptance kriterijumi

- [x] `AuditEvent` model postoji sa tačnim v3.1 poljima (9/9)
- [x] Migracija radi čisto (`alembic upgrade head`/`downgrade -1`,
      ručno provjereno na privremenoj SQLite bazi)
- [x] `write_audit_event` upisuje sve navedene scenarije ispravno (14
      testova, svi prolaze)
- [x] Nema `update`/`delete` funkcije za audit zapise u servisnom sloju
- [x] Postojeći `pytest tests/ -q` (410 passed, 2 skipped — 396+14 novih,
      minus 0 regressed), `ruff`, `mypy`, `agent_sensors.py --all` ostaju
      čisti
- [x] `src/dentaland/services/appointments.py`, `auth.py`,
      `backend/main.py`, `desktop/**` netaknuti (grep potvrda: 0 pogodaka
      za `write_audit_event`/`AuditEvent`/`AuditAction` u tim putanjama)

## Rezultati komandi

```text
pytest tests/ -q          → 410 passed, 2 skipped, 12 warnings
ruff check src/dentaland tests backend  → All checks passed!
mypy src/dentaland backend               → Success: no issues found in 19 source files
python scripts/agent_sensors.py --all    → Result: 0 blocking findings
```

Baseline prije izmjena (za poređenje): 396 passed, 2 skipped; ruff/mypy/
sensors čisti. Razlika: +14 novih testova (test_audit.py), 0 regresija.

## Šta NIJE urađeno (namjerno, van obima)

- Nula instrumentacije stvarnih poziva (`auth.py`, `appointments.py`,
  `backend/main.py`) — radi 014B/014C poslije merge-a.
- `VIEW_PATIENT`/`EXPORT_PERSONAL_DATA`/`DELETE_OR_ANONYMIZE_PERSONAL_DATA`/
  `VIEW_MEDICAL_DATA` enum vrijednosti — van obima, nemaju funkcionalnost.
- `CHANGE_ROLE` endpoint/UI — enum vrijednost definisana, dormant.
- Retention/brisanje job.

## OUT_OF_SCOPE_FINDING

Nijedan. Nije otkriveno ništa što bi zahtijevalo retention/brisanje
logiku ili drugu odluku van obima ovog taska.

## Sljedeći koraci

Task spreman za review (Codex Reviewer 1 obavezan, Pi Reviewer 2). Nakon
merge-a u `main`, `DENT-IMPROVE-014B` (Pi) i `DENT-IMPROVE-014C` (Crush)
mogu početi paralelno.
