---
task_id: DENT-IMPROVE-014C
type: plan
created_at: 2026-08-27
---

# DENT-IMPROVE-014C — Plan (prije prve izmjene koda)

## Cilj

Instrumentisati `create_appointment`, `update_appointment`,
`cancel_appointment`, `delete_appointment` u
`src/dentaland/services/appointments.py` da svaka, na uspjeh, upiše
tačan `AuditEvent` (`resource_type="appointment"`, `resource_id=<id>`,
`actor_user_id=None`) ATOMSKI — unutar iste `with session_factory() as
session:` transakcije, prije `session.commit()`, koristeći
`write_audit_event(session_factory, action, ..., session=session)`.

## Pogođeno

- `src/dentaland/services/appointments.py` — dodati import
  `write_audit_event`, `AuditAction` (iz `dentaland.models`), i po jedan
  poziv u svaku od 4 funkcije, PRIJE `session.commit()`.
- Novi `tests/test_audit_appointments.py` — bihevioralni testovi za sve 4
  operacije + negative-case (overlap ne piše audit) + metadata sadržaj.

## Verifikovano prije početka

- `DENT-IMPROVE-014` jezgro je u `main` (`git log`: `43c838f feat(models):
  DENT-IMPROVE-014`, `41cb94e Merge ... task/DENT-IMPROVE-014-audit-core`).
- `src/dentaland/services/audit.py` postoji, `write_audit_event(...,
  session=None)` prima opcioni već-otvorenu sesiju i tada NE commit-uje
  (`session.add()` samo) — potvrđeno čitanjem koda (linije 79-149).
- `AuditAction` enum (models.py:256-276) sadrži tačno
  `CREATE_APPOINTMENT`, `UPDATE_APPOINTMENT`, `CANCEL_APPOINTMENT`,
  `DELETE_APPOINTMENT` — imena se poklapaju sa kontraktom.
- Sve 4 funkcije postoje u `appointments.py` sa istim imenima/ponašanjem
  kao u kontraktu (linije su se pomjerile neznatno: create ~64, update
  ~94, cancel ~261, delete ~274 — poklapa se sa kontraktom).
- `tests/test_appointments.py` NE postoji (kontrakt ga navodi kao opciju)
  — postojeći bihevioralni testovi za ove funkcije žive u
  `tests/test_services.py` (kroz `AppointmentService` facade) i
  `tests/test_ref03_booking_split.py` (arhitektonski, ne mijenjam). Biram
  NOVI fajl `tests/test_audit_appointments.py` — direktni pozivi
  `appointments.create_appointment(...)` itd. (bez facade), isti fixture
  obrazac kao `tests/test_audit.py`/`tests/test_services.py`.

## Ključne odluke

1. **`metadata_minimal`**: `UPDATE_APPOINTMENT` dobija
   `{"old_status": <str>, "new_status": <str>}` — operativno korisno
   (npr. koji je bio prethodni status), ne medicinski/lično. Za ostale
   (`CREATE`/`CANCEL`/`DELETE`) — `metadata=None` (prazno), jer
   `resource_type="appointment"` + `resource_id` već identifikuju "šta",
   a status prije/poslije nije nejasan (create: nema prethodnog stanja;
   cancel: uvijek SCHEDULED→CANCELLED, fiksno, dakle ne nosi novu
   informaciju; delete: red se briše, nema "novog" stanja).

   Napomena: `update_appointment` trenutno NE mijenja `status` polje
   (samo ime/telefon/email/doktor/uslugu/vrijeme) — status ostaje
   `SCHEDULED` prije i poslije (funkcija eksplicitno zahtijeva
   `appt.status == SCHEDULED` da bi se izvršila, i ne postavlja novi
   status). Zato `old_status`/`new_status` bi uvijek bili identični
   (`"SCHEDULED"`/`"SCHEDULED"`) — nema stvarne operativne vrijednosti.
   ODLUKA: `update_appointment` audit dobija `metadata=None` (prazno),
   isto kao ostale — izbjegava lažan utisak "status se mijenja ovdje"
   kad ne mijenja. `resource_id` + `action=UPDATE_APPOINTMENT` dovoljno
   identifikuju "termin je uređen u X vrijeme". Ovo je odstupanje od
   prijedloga u kontraktu (koji je bio "možda" / opciono), dokumentovano
   ovdje po tačci "implementer odlučuje".

2. **Neuspješan pokušaj** (npr. `OverlapError`/`ValueError` prije
   `session.commit()`): NE auditati — pratim preporuku iz kontrakta.
   Audit poziv se stavlja NAKON svih validacija, NEPOSREDNO PRIJE
   `session.commit()` (dio iste transakcije) — ako bilo koja provjera
   prije toga baci izuzetak, `write_audit_event` se nikad ne pozove.
   Test pokriva ovo eksplicitno (overlap na create/update ne upisuje
   audit red).

3. `actor_user_id=None` eksplicitno (dokumentovano, ne default-slučajno)
   — desktop nema login koncept.

## Šta NE dirati

`src/dentaland/models.py`, `src/dentaland/services/audit.py`,
`src/dentaland/services/auth.py`, `backend/main.py`, `desktop/**`,
`web/**`, `migrations/**`, `tests/test_audit.py` (jezgro testovi),
`tests/test_ref03_booking_split.py` (arhitektonski testovi — provjerit
ću da moje izmjene ne krše facade allowlist, ali test fajl sam ne
mijenjam).

## Plan verifikacije

- `pytest tests/ -q` (cijeli set, uključujući `test_gui/`).
- `ruff check src/dentaland/services/appointments.py
  tests/test_audit_appointments.py`
- `mypy src/dentaland/services/appointments.py` (ili cijeli `src/` ako
  je tako konfigurisano u projektu).
- `python scripts/agent_sensors.py --all` (ako postoji/primjenjivo).

## Rollback

Izmjena je izolovana na 4 mala dodatka (import + poziv prije commit-a) u
jednom fajlu + jedan nov test fajl. Rollback = `git checkout --
src/dentaland/services/appointments.py` i brisanje
`tests/test_audit_appointments.py`.

## Odbačene opcije

- Audit poziv POSLIJE `session.commit()` u istoj `with` bloku, ali kao
  poseban `write_audit_event(session_factory, ...)` bez `session=` —
  ODBAČENO: nije atomski (dvije odvojene transakcije, izmjena termina
  može uspjeti a audit ne, ili obrnuto). Kontrakt eksplicitno traži
  atomičnost.
- Auditovati i neuspješne pokušaje (npr. `OverlapError`) radi potpunije
  evidencije — ODBAČENO, pratim preporuku kontrakta: funkcija koja baci
  izuzetak nije promijenila stanje, manja compliance vrijednost, a
  dodaje šum (svaki drag&drop preklop bi pravio audit red).
- `metadata` sa `old_status`/`new_status` za `update_appointment` kao što
  je predloženo u kontraktu — ODBAČENO jer `update_appointment` ne mijenja
  status (vidi odluku #1 gore), pa bi polje bilo konstantno i besmisleno.
