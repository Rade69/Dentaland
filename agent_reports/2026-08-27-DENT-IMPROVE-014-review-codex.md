# DENT-IMPROVE-014 — Codex independent review

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS_WITH_NOTES
blocking_findings: []
```

## CILJ

Nezavisno provjeriti append-only audit jezgro, tačnost v3.1 šeme, migraciju i
javni API potreban za samostalni 014B upis i atomski 014C upis.

Review je urađen nad eksplicitno predatim nekomitovanim snapshotom grane
`task/DENT-IMPROVE-014-audit-core`.

## URAĐENO

**PASS_WITH_NOTES.** Nije potvrđen specifikacijski, kodni ni arhitektonski
defekt u pregledanom scope-u.

### Šema i migracija

- `AuditEvent` ima tačno svih 9 v3.1 polja: `id`, `actor_user_id`, `action`,
  `resource_type`, `resource_id`, `occurred_at`, `request_id`, `source_ip`,
  `metadata_minimal`.
- Nullable ugovor je ispravan; `actor_user_id` je nullable FK na `users.id`.
- `AuditAction` ima tačno 7 Radovanom odobrenih vrijednosti. `CHANGE_ROLE` je
  definisan, ali nema pozivaoca.
- Nova migracija ima `down_revision = e5f6a7b8c9d0`; `alembic heads` daje
  `f6a7b8c9d0e1 (head)`.
- Disposable SQLite upgrade kreirao je `audit_events` sa tačno 9 kolona.
  Downgrade `-1` uklonio je samo audit tabelu i sačuvao svih sedam ranijih
  tabela.

### Atomski `session=` API — nezavisna 014C simulacija

Sopstvena proba nije samo rollbackovala audit red. U jednoj otvorenoj ORM
transakciji:

1. kreiran je stvarni `Appointment` i dobijen njegov ID preko `flush()`;
2. pozvan je `write_audit_event(..., session=db)` za isti appointment;
3. izazvan je `RuntimeError` prije pozivaočevog commita.

Rezultat provjeren iz nove sesije:

```text
APPOINTMENT_ROLLED_BACK=True
AUDIT_ROLLED_BACK=True
```

Funkcija sa proslijeđenim `session=` samo radi `session.add()` i ne
commit-uje. Zato 014C može uključiti appointment mutaciju i audit zapis u isti
commit bez privatnog cross-module API-ja. Bez `session=`, funkcija ispravno
otvara i commit-uje vlastitu transakciju za 014B/samostalni slučaj.

### Append-only površina i scope

- `src/dentaland/services/audit.py` javno izlaže samo insert operaciju;
  nema update/delete/mutate funkcije za postojeće audit redove.
- DB-nivo trigger/permisija namjerno ne postoji, prema Radovanovoj odluci;
  direktni SQL ostaje tehnički moguć i to je jasno dokumentovano.
- Nema poziva `write_audit_event` niti `AuditEvent` instrumentacije u
  `appointments.py`, `auth.py`, `backend/main.py`, `desktop/**` ili `web/**`.
- Forbidden paths, postojeće migracije, `migrations/env.py` i `alembic.ini`
  nisu dirani.
- Jedina posljedična izmjena testa je dodavanje `audit_events` u egzaktan set
  svih tabela u `tests/test_models.py`; sadržajno je nužna i mehanička.

## METADATA_MINIMAL PROCJENA

Pozivalac je jasno i višestruko upozoren da `metadata` ne smije sadržati
lozinku, token, medicinski sadržaj, puni request body niti suvišan PII.
Servis namjerno ne validira/sanitizuje dict, a test eksplicitno zaključava taj
ugovor.

To je prihvatljiv kompromis za ovaj ograničeni obim iz dva razloga:

- poznata su samo dva buduća instrumentacijska taska, 014B i 014C, i oba
  imaju eksplicitne testne zabrane za tajne/PII;
- generički denylist ključeva (`password`, `token`, itd.) dao bi lažan osjećaj
  sigurnosti i lako se zaobilazi drugim nazivom ili ugniježđenim sadržajem.

Ovo ipak ostaje sigurnosna napomena: svaki novi pozivalac mora koristiti
action-specific allowlist minimalnih polja i imati test da nema tajne/PII.
Ako broj pozivalaca naraste, centralna action-specific schema/allowlist je
bolji sljedeći korak od generičkog denylista. To nije blocking finding jezgra.

## VERIFIKACIJA

- `pytest tests/test_audit.py -q`: **14 passed**.
- `pytest tests/ -q`: **410 passed, 2 skipped**, 12 warnings.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`:
  **All checks passed**.
- `mypy src/dentaland desktop backend`: **Success**, 54 source fajla.
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.

## NE DIRATI

- Ne instrumentisati login ili appointment tokove u ovom jezgru; to rade
  odvojeni 014B/014C taskovi nakon merge-a.
- Ne širiti enum mimo odobrenih 7 akcija i ne graditi CHANGE_ROLE tok.
- Ne uvoditi DB trigger/retention job bez zasebne odluke.
- Ne izmišljati actor identitet za desktop appointment događaje.

## SLJEDEĆE

Codex Reviewer 1 verdict je **PASS_WITH_NOTES**, bez blocking nalaza. Nakon
Pi Reviewer 2 i Radovan human approval-a, treba commitovati/pushovati i
mergovati tačno pregledano jezgro. Tek tada 014B i 014C mogu početi paralelno.
