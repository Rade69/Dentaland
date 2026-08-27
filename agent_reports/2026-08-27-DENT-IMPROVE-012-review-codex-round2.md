# DENT-IMPROVE-012 — Codex re-review, Fix runda 2

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS_WITH_NOTES
security: PASS
blocking_findings: []
```

## CILJ

Provjeriti da `DATABASE_URL` više ne pregazi Alembic URL koji je pozivalac
eksplicitno postavio, uz očuvanje Fix runde 1, PostgreSQL 409 ponašanja i
SQLite defaulta.

Review je urađen nad eksplicitno predatim nekomitovanim snapshotom grane
`task/DENT-IMPROVE-012-postgres-migration`.

## URAĐENO

**PASS_WITH_NOTES.** Nema potvrđenog defekta u pregledanom Fix runda 2 scope-u.

### Reprodukcija originalnog kombinovanog uslova

Obje varijable iz ignorisanog `.env` fajla postavljene su istovremeno, nakon
što je nezavisno potvrđeno da oba URL-a ciljaju isključivo port 5433.
Kredencijali nisu ispisivani.

Četiri prethodno pogođena testa:

```text
4 passed, 9 warnings
```

Time je potvrđeno da programski `Config.set_main_option()` URL-ovi za
izolovane `tmp_path` SQLite baze ostaju autoritativni i da Alembic više ne
odlazi tiho na PostgreSQL.

### F1 i PostgreSQL ponašanje

- `pytest tests/test_postgres_migration.py -q`: **2 passed**;
- percent-encoded password test i dalje ide kroz stvarni subprocess
  `alembic current`/`migrations/env.py`;
- PostgreSQL overlap scenario i dalje vraća HTTP 409;
- `alembic current` sa env overrideom: `d4e5f6a7b8c9 (head)`.

### Puni regression sweep

- obje varijable istovremeno: `pytest tests/ -q` → **376 passed**;
- bez `DATABASE_URL` i `DATABASE_URL_TEST`: **374 passed, 2 skipped**;
- Ruff nad projektnim scope-om i novim migratorom: **All checks passed**;
- `mypy src/dentaland desktop backend`: **Success**, 52 source fajla;
- `python scripts/agent_sensors.py --all`: **0 blocking findings**.

### Guard i pozivaoci

Pregledani su svi repo pozivaoci `Alembic Config`, `set_main_option` i
`command.upgrade/downgrade`. Jedina četiri programska URL overridea koriste
jedinstvene `tmp_path` URL-ove, različite od `sqlite:///dentaland.db`.
CLI Alembic put ostavlja ini default netaknut i zato ispravno prima
`DATABASE_URL` override.

Guard ima neizbježnu semantičku neodređenost: budući pozivalac koji
eksplicitno postavi baš string `sqlite:///dentaland.db` ne može se razlikovati
od neizmijenjenog ini defaulta, pa bi env varijabla pobijedila. Takav pozivalac
ne postoji u trenutnom kodu/testovima, a ta vrijednost upravo predstavlja
default metu koju `DATABASE_URL` treba zamijeniti. Ovo je residualna napomena,
ne trenutni defekt niti blocking finding.

### Scope i pravno blokirani dio

Fix runda 2 mijenja samo `migrations/env.py`; postojeći testovi nisu dirani.
Ponovljeni grep nalazi `EXCLUDE`/`btree_gist` samo u backlog dokumentaciji
koja opisuje namjerno odgođeni rad. Nema PostgreSQL ekstenzije, constrainta ni
izmjene `migrations/versions/**`.

## NE DIRATI

- Ne uvoditi `EXCLUDE`/`btree_gist` bez zasebne pravne i projektne odluke.
- Ne mijenjati postojeće Alembic revision fajlove radi ovog fixa.
- Ne koristiti port 5432 niti stvarne pacijentske podatke u verifikaciji.

## SLJEDEĆE

Codex Fix runda 2 re-review je **PASS_WITH_NOTES**, bez blocking nalaza.
Snapshot može nastaviti Revieweru 2 i zatim Radovan human approval-u. Prije
toga treba commitovati i pushovati tačno pregledano stanje, jer je worktree
trenutno nekomitovan.
