# DENT-IMPROVE-014C — Codex re-review, Fix runda 1

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## CILJ

Provjeriti da je prethodna testna napomena zatvorena stvarnim regresionim
testom koji razlikuje atomski appointment+audit upis od dvije transakcije.

Review je urađen nad eksplicitno predatim nekomitovanim snapshotom grane
`task/DENT-IMPROVE-014C-audit-appointments`.

## URAĐENO

**PASS_WITH_NOTES.** Prethodna testna napomena je zatvorena; nema blocking
nalaza niti potvrđenog defekta u Fix runda 1 scope-u.

### Novi test je genuina regresiona zaštita

`test_create_appointment_kvar_poslije_audit_poziva_rollbackuje_oboje` cilja
tačno simbol `appointments.write_audit_event` koji produkcijska funkcija
poziva. Wrapper:

1. pozove stvarni `dentaland.services.audit.write_audit_event` sa originalnim
   argumentima, uključujući produkcijski `session=`;
2. tek nakon stvarnog audit `add()` podigne `RuntimeError`;
3. time prekine `create_appointment` prije njegovog `session.commit()`.

Završna provjera otvara novu sesiju i zahtijeva:

- nula trajno upisanih appointment redova;
- nula trajno upisanih audit redova.

To je isti mehanizam i ista dva postuslova kao nezavisna Codex adversarna
proba iz prvog reviewa. Ciljani test je svježe pokrenut i daje **1 passed**;
cijeli novi fajl daje **9 passed**.

### Da li je jedan create test dovoljan?

Za acceptance i trenutni kod: **da**. Create je najzahtjevniji predstavnik
jer uključuje `flush()` autoincrement inserta prije audit poziva. Test zato
dokazuje da čak i već-flushovan poslovni red ostaje dio necommitovane
transakcije i nestaje zajedno s audit redom.

UPDATE, CANCEL i DELETE imaju jednostavniji isti obrazac: poslovna promjena,
`write_audit_event(..., session=session)`, jedan pozivaočev commit. Svaki ima
poseban happy-path test sa tačnim action/resource ID-em, a stvarni kod je
ponovo vizuelno provjeren.

Residualna preporuka: jedan parametrizovan/spy test koji za sva četiri
pozivna mjesta potvrđuje da je proslijeđen isti ORM `session` dodatno bi
štitio od lokalne buduće greške samo u UPDATE/CANCEL/DELETE pozivu. Četiri
duplirana failure-path testa nisu potrebna sada i njihov izostanak nije
blocking.

## VERIFIKACIJA

- atomski regresioni test: **1 passed**;
- `pytest tests/test_audit_appointments.py -q`: **9 passed**;
- `pytest tests/ -q`: **419 passed, 2 skipped**, 12 warnings;
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`:
  **All checks passed**;
- `mypy src/dentaland desktop backend`: **Success**, 54 source fajla;
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.

## NE DIRATI

- Ne širiti fix na produkcijski kod; atomska implementacija je već ispravna.
- Ne dodavati PII metadata, desktop actor identitet ili audit neuspjelih
  overlap pokušaja.
- Ne mijenjati audit jezgro, auth/backend, UI ili migracije.

## SLJEDEĆE

Codex re-review je **PASS_WITH_NOTES**, bez blocking nalaza. Snapshot može ići
Pi Revieweru 2 i zatim Radovan human approval-u. Prije merge-a treba
commitovati i pushovati tačno pregledano stanje.
