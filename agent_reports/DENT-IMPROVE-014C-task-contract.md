---
task_id: DENT-IMPROVE-014C
risk: HIGH
implementer: crush
reviewers: [codex, pi]
status: "NOT STARTED — čeka DENT-IMPROVE-014 (jezgro) merge u main prije početka."
created_at: 2026-08-27
depends_on: DENT-IMPROVE-014
---

# DENT-IMPROVE-014C — Audit: CREATE/UPDATE/CANCEL/DELETE_APPOINTMENT

## Zavisnost — NE POČINJI dok se ovo ne provjeri

Ovaj task uvozi `AuditEvent`/`write_audit_event` iz
`DENT-IMPROVE-014` (jezgro). **Provjeri prije bilo čega**: da li je
`src/dentaland/services/audit.py` i `AuditEvent` model stvarno u `main`
(`git log --oneline main | grep DENT-IMPROVE-014`, i
`ls src/dentaland/services/audit.py` nakon `git pull`). Ako nije
mergovano, STANI i javi — ne pravi svoju kopiju/duplikat tih fajlova.

## Kontekst

Paralelan par sa `DENT-IMPROVE-014B` (implementer Pi) — nula preklapanja
fajlova (potvrđeno u `DENT-IMPROVE-014` kontraktu prije starta oba
taska).

**Bitno arhitektonsko ograničenje (Radovanova odluka, već donesena, ne
re-otvaraj):** desktop app nema koncept ulogovanog korisnika. Pošto se
ove četiri funkcije pozivaju skoro isključivo iz desktopa (preko
`AppointmentService` fasade), audit zapisi koje ovaj task pravi će imati
`actor_user_id = NULL`. Ovo je PRIHVAĆENO ograničenje, ne nedostatak
tvog rada — ne pokušavaj "riješiti" ga izmišljanjem lažnog actor-a ili
proširivanjem obima na desktop login.

## Trenutno stanje (provjereno 27.8.2026)

`src/dentaland/services/appointments.py` sadrži:
- `create_appointment(...)` (linija ~64)
- `update_appointment(...)` (linija ~94)
- `cancel_appointment(session_factory, appt_id)` (linija ~261)
- `delete_appointment(session_factory, appt_id)` (linija ~274)

Sve četiri su JEDINA zajednička tačka — `AppointmentService` fasada u
`src/dentaland/services/booking.py` samo delegira ovim funkcijama
(`self._store.cancel(id)` → `appointments.cancel_appointment(...)`, itd.).
Instrumentacija OVDJE (ne u `booking.py` fasadi, ne u desktop kontrolerima)
pokriva sav stvaran saobraćaj.

## Cilj

Svaka od četiri funkcije upisuje tačan `AuditEvent` (`resource_type="appointment"`,
`resource_id=<id termina>`, `actor_user_id=None`) POSLIJE uspješne izmjene
(u istoj transakciji/commit-u kao i sama izmjena, ne poseban poziv poslije
— izbjegava scenario gdje izmjena uspije a audit zapis ne, ili obrnuto;
isti princip atomičnosti kao `DENT-IMPROVE-013` Fix runda 1 F1).

## Required scope

1. Dodati `write_audit_event(...)` poziv u svaku od 4 funkcije, UNUTAR
   iste `with session_factory() as session:` transakcije gdje se sama
   izmjena termina commit-uje (provjeri kako `write_audit_event` prima
   sesiju/session_factory — ako prima `session_factory` i sam otvara
   svoju transakciju, to NIJE atomski sa izmjenom termina; ako je to
   slučaj, prijavi kao `OUT_OF_SCOPE_FINDING` implementeru jezgra i
   predloži da `write_audit_event` prihvati i opcioni već-otvoren
   `session` parametar za ovaj tačan scenario — isti obrazac kao
   `_revoke_active_sessions` helper iz `DENT-IMPROVE-013` Fix runde 1).
2. `metadata_minimal`: implementer odlučuje šta je korisno a nije
   PII/medicinski sadržaj. Prijedlog: za `UPDATE_APPOINTMENT`, možda
   `{"old_status": ..., "new_status": ...}` (operativno korisno, ne
   medicinski/lično) — OPCIONO, ne obavezno. Za ostale, prazno je
   prihvatljivo (resource_type+resource_id već identifikuju "šta").
   **Nikad ime/telefon/email pacijenta, nikad napomena polje.**
3. Odluka: da li se audit piše i na NEUSPJEŠAN pokušaj (npr. `OverlapError`
   baci grešku prije commit-a) — preporuka: NE, auditati samo stvarne
   uspješne mutacije (funkcija koja baci izuzetak nije promijenila
   stanje, manje compliance vrijednosti u bilježenju pokušaja). Implementer
   može odstupiti uz dokumentovan razlog.
4. `CREATE_APPOINTMENT`/`DELETE_APPOINTMENT` — provjeri da li ove funkcije
   uopšte postoje sa tim tačnim imenima i ponašanjem (kontrakt navodi
   linije iz provjere 27.8.2026 — mogle su se pomjeriti, provjeri sam
   prije pisanja koda).
5. Testovi (dopuna `tests/test_appointments.py` ili novi
   `tests/test_audit_appointments.py`):
   - Svaka od 4 operacije upisuje tačno JEDAN audit red sa ispravnim
     `action`/`resource_id`.
   - `actor_user_id` je `NULL` (dokumentovano očekivano ponašanje, ne
     bug).
   - Neuspješan pokušaj (npr. overlap na create/update) NE upisuje audit
     red (ili DOK ako je implementer odlučio drugačije — test prati
     stvarnu odluku).
   - `metadata_minimal` nikad ne sadrži ime/telefon/email/napomenu
     pacijenta.

## Šta NE dirati

- `src/dentaland/models.py`, `src/dentaland/services/audit.py` (jezgro —
  samo POZIVAJ `write_audit_event`, prijavi nalaz ako treba izmjena, ne
  mijenjaj direktno bez dogovora).
- `src/dentaland/services/auth.py`, `backend/main.py` (`DENT-IMPROVE-014B`
  posao).
- `desktop/**`, `web/**` (instrumentacija u `appointments.py` pokriva
  desktop saobraćaj bez diranja desktop koda).
- Ne pokušavati dodati actor_user_id popunjavanje izmišljanjem desktop
  login mehanizma — van obima, Radovanova odluka.

## Acceptance criteria

- [ ] Sve 4 operacije (create/update/cancel/delete) upisuju tačan audit
      zapis na uspjeh
- [ ] Audit upis je atomski sa samom izmjenom (ili je neatomskost
      prijavljena kao nalaz, ne tiho ostavljena)
- [ ] `actor_user_id=NULL` (dokumentovano, ne bug)
- [ ] `metadata_minimal` nikad ne sadrži lične/medicinske podatke
- [ ] Postojeći `pytest tests/ -q` (uključujući desktop GUI testove koji
      koriste ove funkcije), `ruff`, `mypy`, `agent_sensors.py --all`
      ostaju čisti
- [ ] `auth.py`, `backend/main.py`, `desktop/**` netaknuti

## Allowed paths

```text
src/dentaland/services/appointments.py
tests/test_appointments.py               (ili novi tests/test_audit_appointments.py)
agent_reports/**
```

## Forbidden paths

```text
src/dentaland/models.py
src/dentaland/services/audit.py
src/dentaland/services/auth.py
backend/main.py
desktop/**
web/**
migrations/**
```

## Review

Codex (Reviewer 1, obavezan, v3.1 princip #7) + Pi (Reviewer 2, pošto je
Crush implementer — nezavisna sesija/agent).

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-014C --agent crush --paths src/dentaland/services/appointments.py
```

Paralelno sa `DENT-IMPROVE-014B` (Pi) — provjeri `coordination.py status`
prije starta da potvrdiš da nema konflikta.
