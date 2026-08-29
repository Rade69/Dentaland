# Dentaland — operativni PostgreSQL backup (DENT-IMPROVE-016)

Ovaj vodič opisuje kako se backup PostgreSQL baze (Faza 1+) pokreće ručno
i kroz scheduler. Paralelan je uz
[dentaland-backup-operativni-vodic.md](dentaland-backup-operativni-vodic.md)
(SQLite, Faza 0) — ne zamjenjuje ga, koristi se kad aplikacija radi
protiv PostgreSQL-a (`DATABASE_URL` postavljen).

Backup koristi stvarne `pg_dump`/`pg_restore` izvršne fajlove (ne
reimplementira dump logiku u Pythonu), format `custom` (`-Fc`,
kompresovan). Engine: `src/dentaland/backup_postgres.py`.

## Tri komande

```text
python -m dentaland.backup_postgres run           — kreiraj enkriptovan pg_dump odmah
python -m dentaland.backup_postgres restore-test   — restore najnovijeg backupa u PRIVREMENU
                                                     bazu, verifikuj, pa je obriši
python -m dentaland.backup_postgres status         — kad je zadnji uspješan backup
```

Sve tri vraćaju **non-zero exit kod** (1) kad nešto ne uspije, i ispisuju
jasnu poruku na stderr — to je ono što scheduler/log vidi kao failure.

## Preduslovi

- `DATABASE_URL` mora biti postavljen (SQLAlchemy URL PostgreSQL baze koja
  se backup-uje).
- `pg_dump`/`pg_restore` moraju biti dostupni — redoslijed pretrage:
  1. `DENTALAND_PG_BIN_DIR` (eksplicitni override, folder sa izvršnim
     fajlovima);
  2. PATH (produkcija na Linux VPS-u normalno ima ovo kroz
     `postgresql-client` paket);
  3. standardna Windows instalacija (`C:\Program Files\PostgreSQL\<verzija>\bin\`)
     — dev convenience, ne oslanjati se na ovo u produkciji.
- Pokretanje iz korijena repoa, uz `PYTHONPATH=src`:

```powershell
cd C:\Users\<korisnik>\Desktop\Dentaland
$env:PYTHONPATH = "src"
$env:DATABASE_URL = "postgresql://..."
python -m dentaland.backup_postgres run
```

## Razlike u odnosu na SQLite backup (namjerne)

| | SQLite (`dentaland.backup`) | PostgreSQL (`dentaland.backup_postgres`) |
|---|---|---|
| Alat | `sqlite3.Connection.backup()` | `pg_dump`/`pg_restore` (subprocess) |
| Enkripcija | Fernet, ključ `backup.key` | Fernet, **poseban** ključ `backup_postgres.key` |
| Rotacija | dnevno (30) + mjesečno (3) | zadrži zadnjih `daily_keep` (default 30), bez mjesečnog sloja |
| Restore-test destinacija | zaseban plain `.db` fajl, obrisan nakon provjere | privremena baza (`CREATE`/`DROP DATABASE`), obrisana nakon provjere |

Rotacija je namjerno pojednostavljena — za obim jedne ordinacije
dvoslojna dnevna/mjesečna šema (kao kod SQLite) nije neophodna
(CLAUDE.md: proporcionalno obimu, ne enterprise default).

**Zašto poseban ključ:** SQLite i PostgreSQL backup ključevi su odvojeni
namjerno — curenje jednog ključa ne kompromituje drugi domen backupa.

## Gdje idu podaci

Iste centralne putanje kao SQLite backup
(`src/dentaland/paths.py`), plus `postgres/` podfolder da se dump
fajlovi ne miješaju sa `.db.enc` fajlovima:

| Putanja | Default |
|---|---|
| Lokalni backup folder | `data_dir()/backups/postgres` |
| Cloud/sync folder | `DENTALAND_BACKUP_CLOUD_DIR` override, inače lokalni |
| Ključ za enkripciju | `data_dir()/config/backup_postgres.key` (odvojen od SQLite ključa) |

**Ključ za enkripciju je namjerno izvan backup foldera** — isto pravilo
kao SQLite backup, ne kopirati ga u backup/cloud folder.

## `restore-test` — kako radi

1. Dekriptuje najnoviji `.dump.enc` u privremeni plain `.dump` fajl.
2. Poveže se na POSTOJEĆU bazu (`DATABASE_URL`) kao admin konekciju i
   kreira privremenu bazu (ime izvorne baze + `_restore_check`, npr.
   `dentaland_dev_restore_check`) — ako već postoji od prekinutog
   prethodnog pokušaja, prvo je obriše.
3. `pg_restore` upisuje dump U TU privremenu bazu — aktivna baza
   (`DATABASE_URL`) se NIKAD ne dira ovim korakom.
4. Provjerava da je privremena baza čitljiva (`SELECT COUNT(*) FROM
   appointments`).
5. Obriše privremenu bazu i plain `.dump` fajl, bez obzira na ishod
   provjere (`finally`).

## Testiran, ne samo napravljen

CLAUDE.md zahtjev: "Dnevni `pg_dump` backup (Faza 1+) + **testiran**
restore, ne samo napravljen." — `restore-test` komanda postoji upravo
zbog ovog zahtjeva. Preporuka: pokretati `run` dnevno (scheduler), a
`restore-test` bar sedmično (potvrđuje da su backupi stvarno upotrebljivi,
ne samo da fajl postoji).

## Poznato ograničenje (van obima DENT-IMPROVE-016)

Ovaj modul backup-uje/restore-uje PODATKE i ŠEMU kakvi jesu u trenutku
`pg_dump`-a — ne provjerava da li je `alembic_version` pečat izvorne baze
usklađen sa stvarnim migration chain head-om. Vidi
`.agent/CURRENT_STATE.md` (OUT_OF_SCOPE_FINDING, 29.8.2026, budući
`DENT-IMPROVE-017`) za poznatu neusklađenost na lokalnoj dev/test
instanci — ne utiče na ispravnost backup/restore operacije same po sebi.
