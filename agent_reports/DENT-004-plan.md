# Plan — DENT-004 (MEDIUM)

## Cilj
Backup SQLite baze: `sqlite3.Connection.backup()` → lokalno plain `.db` →
enkripcija (Fernet) → sync folder; rotacija, evidencija, restore sa round-trip.

## Pogođeno
- Novi modul `src/dentaland/backup.py`.
- `pyproject.toml` — samo dodati `cryptography>=42.0` u dependencies.
- Novi testovi `tests/test_backup.py`.
- `agent_reports/DENT-004-plan.md` (ovaj fajl).

## Plan
1. `backup.py`: `BackupConfig` (db_path, local_dir, cloud_dir, key_path,
   daily_keep=30, monthly_keep=3).
2. `backup_database()` isključivo kroz SQLite backup API; `_encrypt`/`_decrypt`
   kroz Fernet (autentifikovana enkripcija, tamper-evident).
3. `ensure_key` (generiši ako nema) vs `load_key` (restore — greška ako nema).
4. `create_backup(config)` — tok: plain lokalno → enkriptuj → obriši plain →
   `rotate_backups` → `_write_last_backup`.
5. `restore_backup(config, enc, dest)` — dekriptuj u plain `.db`.
6. Rotacija kao čista funkcija `_backups_to_delete(files, daily_keep,
   monthly_keep)` (testabilna bez diska) + `rotate_backups` (briše sa diska).

## Šta NE dirati
`src/dentaland/models.py`, `migrations/**`, `desktop/**`, `CLAUDE.md`,
`AGENTS.md`, `docs/**`. U `pyproject.toml` samo jedan novi red; SQLAlchemy /
alembic / tzdata / PySide6 redovi ostaju netaknuti.

## Plan verifikacije
- `pytest tests/test_backup.py -v`
- `ruff check src/dentaland/backup.py`

## Rollback
Novi kod na grani `task/DENT-004-backup`; ništa postojeće se ne mijenja osim
jednog reda u `pyproject.toml` (lako reverzibilno). Nema commit-a bez naloga.

## Odbačene opcije
- `shutil.copy`/sirovo kopiranje `.db` — zabranjeno (WAL nekonzistentnost).
- `sqlcipher3` — namijenjen M1 modulu, ne opštem backupu baze.
- PyNaCl `SecretBox` — dodatna zavisnost bez prednosti nad Fernet za ovaj obim.
- AES-GCM ručno — Fernet već daje autentifikovanu enkripciju, manje prostora za grešku.
