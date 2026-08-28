# DENT-IMPROVE-014C — Codex independent review

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS_WITH_NOTES
blocking_findings: []
```

## CILJ

Provjeriti da CREATE/UPDATE/CANCEL/DELETE appointment mutacije upisuju
minimalan, PII-free audit zapis atomski sa poslovnom izmjenom.

Review je urađen nad eksplicitno predatim nekomitovanim snapshotom grane
`task/DENT-IMPROVE-014C-audit-appointments`.

## URAĐENO

**PASS_WITH_NOTES.** Nije potvrđen specifikacijski, kodni, arhitektonski ni
sigurnosni defekt u pregledanom scope-u.

### Četiri transakcijska toka

U sve četiri funkcije stvarni kod slijedi isti ispravan redoslijed:

1. učita/validira i primijeni poslovnu mutaciju;
2. pozove `write_audit_event(..., session=session)`;
3. pozove jedini `session.commit()` koji trajno upisuje oboje.

Audit pozivi su zato u istoj ORM sesiji/transakciji kao appointment mutacija,
ne u samostalnoj audit transakciji poslije poslovnog commita.

Nezavisna adversarna proba zamijenila je importovani audit poziv wrapperom
koji prvo izvrši stvarni `write_audit_event`, a zatim baci `RuntimeError`
prije `create_appointment` commita. Provjera iz nove sesije dala je:

```text
ERROR=RuntimeError
APPOINTMENT_ROLLED_BACK=True
AUDIT_ROLLED_BACK=True
```

Time je direktno potvrđen 014C atomski invariant, ne samo happy path.
UPDATE, CANCEL i DELETE koriste identičnu `session=session`/jedan-commit
strukturu i pregledani su pojedinačno.

### `flush()`, delete ID i status/metadata odluka

- `create_appointment` radi `session.flush()` nakon `session.add(appt)`.
  To je potrebno jer je `Appointment.id` autoincrement vrijednost koju audit
  mora dobiti prije commita. Flush ostaje unutar iste transakcije, pa
  adversarni rollback uklanja i već-flushovan appointment red.
- `delete_appointment` koristi ulazni `appt_id` kao `resource_id`. To je
  ispravan i stabilan identifikator resursa koji se briše. ORM objekat bi u
  ovom trenutku praktično još imao `appt.id` dok je samo označen za brisanje,
  pa objašnjenje „objekat je već delete-ovan“ nije strogo neophodno, ali izbor
  ulaznog ID-a nije greška i daje isti tačan rezultat.
- `update_appointment` provjerava da je status `SCHEDULED`, ali mijenja samo
  pacijent/contact, doctor/service, note i vrijeme. Nema assignmenta na
  `appt.status`. `old_status/new_status` metadata bi zato bila konstantna i
  zavaravajuća; odluka `metadata=None` je opravdana.
- Sva četiri audit poziva izostavljaju `metadata`, pa
  `metadata_minimal=None`. Ime, telefon, email i napomena nigdje se ne
  prosleđuju audit servisu.

### Neuspješni pokušaji i scope

- Create/update overlap se desi prije audit poziva; oba testa potvrđuju da
  broj audit redova ostaje nepromijenjen.
- Nepostojeći termin/pogrešan cancel status takođe dižu prije audit poziva.
- `actor_user_id=None` je eksplicitan na sva četiri mjesta, prema prihvaćenom
  desktop ograničenju.
- Forbidden `models.py`, audit jezgro, `auth.py`, `backend/main.py`,
  `desktop/**`, `web/**` i `migrations/**` nisu dirani.
- Izmjena Task Contracta je samo ispravka implementer atribucije koju je
  Radovan već odobrio.

## TESTNA NAPOMENA

Novi suite dobro pokriva četiri uspješna toka, dva overlap neuspjeha i
odsustvo PII. Međutim, njegov module docstring tvrdi da pokriva „atomičnost
(rollback ne upisuje ništa trajno)“, a nijedan od osam testova ne izaziva
kvar poslije audit `add()` i prije commita. Postojeći testovi bi zato slabije
štitili od buduće regresije transakcijske granice nego nezavisna proba iz
ovog reviewa.

Ovo nije blocking finding jer Task Contract nije izričito zahtijevao
committed failure-path test, stvarna implementacija je atomska, a obavezna
reviewer proba je to nezavisno dokazala. Ipak, za HIGH audit invariant
preporučujem naknadno pretvoriti isti wrapper/rollback scenario u trajni test.

## VERIFIKACIJA

- `pytest tests/test_audit_appointments.py -q`: **8 passed**.
- `pytest tests/ -q`: **418 passed, 2 skipped**, 12 warnings.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`:
  **All checks passed**.
- `mypy src/dentaland desktop backend`: **Success**, 54 source fajla.
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.

## NE DIRATI

- Ne izmišljati desktop actor identitet.
- Ne dodavati PII/medicinski sadržaj u metadata.
- Ne auditati neuspješne overlap pokušaje u ovom tasku.
- Ne mijenjati audit jezgro, auth/backend ili UI slojeve.

## SLJEDEĆE

Codex Reviewer 1 verdict je **PASS_WITH_NOTES**, bez blocking nalaza. Nakon
Pi Reviewer 2 i Radovan human approval-a treba commitovati/pushovati i
mergovati tačno pregledano stanje.
