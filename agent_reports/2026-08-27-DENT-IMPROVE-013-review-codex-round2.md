# DENT-IMPROVE-013 — Codex re-review, Fix runda 1

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS_WITH_NOTES
security: PASS
blocking_findings: []
```

## CILJ

Provjeriti da su password hash promjena i opoziv svih postojećih sesija sada
jedna atomska transakcija, uz očuvanje javnih session helpera i RBAC toka.

Review je urađen nad eksplicitno predatim nekomitovanim snapshotom grane
`task/DENT-IMPROVE-013-auth-rbac`.

## URAĐENO

**PASS_WITH_NOTES.** Prethodni HIGH F1 je zatvoren. Nema potvrđenog defekta u
pregledanom Fix runda 1 scope-u.

### Nezavisna adversarna reprodukcija

Bez korištenja implementerovog testa, u disposable in-memory bazi kreirani su
korisnik i dvije sesije. Privatni `_revoke_active_sessions` privremeno je
zamijenjen funkcijom koja baca `RuntimeError` prije commita, odnosno istim
failure pathom koji je ranije ostavljao parcijalno stanje.

Stvarni rezultat sa popravljenim kodom:

```text
ERROR=RuntimeError
OLD_PASSWORD_PRESERVED=True
NEW_PASSWORD_NOT_COMMITTED=True
SESSION_PRESERVED_AFTER_ROLLBACK=True
```

To potvrđuje da zatvaranje ORM contexta rollbackuje cijelu necommitovanu
transakciju: nije upisan ni novi hash ni `revoked_at`. Više ne postoji stanje
„nova lozinka trajno upisana, stare sesije ostale validne“ iz prethodnog F1.

### Javni revoke helper

Nakon vraćanja stvarnog helpera, nezavisna proba pozvala je
`invalidate_all_sessions_for_user` nad dvije važeće sesije:

```text
PUBLIC_REVOKE_FIRST_INVALID=True
PUBLIC_REVOKE_SECOND_INVALID=True
PUBLIC_REVOKE_IDEMPOTENT=True
```

Javni API zato i dalje zasebno opoziva sve aktivne sesije, commit-uje rezultat
i ostaje idempotentan.

### Regresiona površina

- `_revoke_active_sessions` prima postojeću ORM sesiju i nema vlastiti commit.
- `change_password` postavlja hash, opoziva sesije i radi tačno jedan commit.
- `invalidate_all_sessions_for_user` koristi isti helper, ali zadržava svoj
  samostalni transaction/commit ugovor.
- `invalidate_session` i `validate_session` nisu promijenjeni; fokusirani auth
  suite pokriva login, logout, expiration/revocation, RBAC i password tokove.
- Novi regresioni test za atomskost genuinski provjerava rollback starog
  password hasha i sesije, ne samo da je izuzetak podignut.

## VERIFIKACIJA

- `pytest tests/test_auth.py -q`: **21 passed**.
- `pytest tests/ -q`: **395 passed, 2 skipped**, 12 warnings.
- `ruff check src/dentaland desktop backend tests scripts/create_user.py
  scripts/agent_sensors.py`: **All checks passed**.
- `mypy src/dentaland desktop backend`: **Success**, 53 source fajla.
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.

## NAPOMENA

Login i `create_session` su i dalje dva servisna koraka/transakcije. Budući
password-change endpoint mogao bi imati usku konkurentnu trku gdje je stara
lozinka provjerena neposredno prije promjene, a nova sesija kreirana poslije
opoziva. U trenutnom scope-u nema password-change endpointa niti drugog
konkurentnog pozivaoca `change_password`, pa ovo nije trenutni blocking
defekt. Kad se uvede mrežni password-change/admin tok, autentifikaciju,
password-version/session issuance ili odgovarajuće zaključavanje treba ponovo
pregledati kao zaseban security invariant.

## NE DIRATI

- Ne širiti ovu fix rundu na OAuth/SSO/2FA, signup UI ili audit tabelu.
- Ne mijenjati RECEPTION-only RBAC niti dodavati ADMIN bypass.
- Ne dirati klijente, postojeće poslovne servise ili stare migracije.

## SLJEDEĆE

Codex re-review je **PASS_WITH_NOTES**, bez blocking nalaza. Snapshot može ići
Revieweru 2 i zatim Radovan human approval-u. Prije toga treba commitovati i
pushovati tačno pregledano stanje, jer je worktree trenutno nekomitovan.
