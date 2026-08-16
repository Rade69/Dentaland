"""Testovi za backup mehanizam (DENT-004)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from cryptography.fernet import Fernet

from dentaland.backup import (
    BACKUP_SUFFIX,
    LAST_BACKUP_FILENAME,
    BackupConfig,
    BackupError,
    _backups_to_delete,
    create_backup,
    ensure_key,
    load_key,
    restore_backup,
    rotate_backups,
)

SARAJEVO = ZoneInfo("Europe/Sarajevo")
NOW = datetime(2026, 8, 16, 12, 0, tzinfo=SARAJEVO)


@pytest.fixture()
def source_db(tmp_path: Path) -> Path:
    db = tmp_path / "src" / "dentaland.db"
    db.parent.mkdir()
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE doctors (id INTEGER PRIMARY KEY, ime TEXT)")
    conn.execute("CREATE TABLE services (id INTEGER PRIMARY KEY, naziv TEXT)")
    conn.execute("INSERT INTO doctors (id, ime) VALUES (1, 'Ljubo')")
    conn.execute("INSERT INTO services (id, naziv) VALUES (1, 'Kontrola'), (2, 'Plomba')")
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def config(tmp_path: Path, source_db: Path) -> BackupConfig:
    return BackupConfig(
        db_path=source_db,
        local_dir=tmp_path / "local",
        cloud_dir=tmp_path / "cloud",
        key_path=tmp_path / "keys" / "backup.key",
    )


def _snapshot(db_path: Path) -> dict[str, list[tuple]]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    tables = [
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    result: dict[str, list[tuple]] = {}
    for table in tables:
        result[table] = cur.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
    conn.close()
    return result


def test_round_trip_backup_restore_identicna_baza(
    config: BackupConfig, source_db: Path, tmp_path: Path
) -> None:
    enc = create_backup(config, now=NOW)
    assert enc.exists()
    assert enc.name == f"dentaland-2026-08-16{BACKUP_SUFFIX}"

    restored = tmp_path / "restored.db"
    restore_backup(config, enc, restored)
    assert _snapshot(source_db) == _snapshot(restored)


def test_backup_radi_dok_je_baza_otvorena(
    config: BackupConfig, source_db: Path, tmp_path: Path
) -> None:
    conn = sqlite3.connect(str(source_db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("INSERT INTO services (id, naziv) VALUES (3, 'Izbjeljivanje')")
    conn.commit()
    try:
        enc = create_backup(config, now=NOW)
        restored = tmp_path / "restored.db"
        restore_backup(config, enc, restored)
        assert _snapshot(restored)["services"] == [
            (1, "Kontrola"),
            (2, "Plomba"),
            (3, "Izbjeljivanje"),
        ]
    finally:
        conn.close()


def test_cloud_sadrzi_samo_enkriptovane_fajlove(config: BackupConfig) -> None:
    create_backup(config, now=NOW)
    names = {p.name for p in config.cloud_dir.iterdir()}
    assert names == {f"dentaland-2026-08-16{BACKUP_SUFFIX}", LAST_BACKUP_FILENAME}
    assert not any(p.suffix == ".db" for p in config.cloud_dir.iterdir())


def test_kljuc_je_odvojen_od_backup_foldera(config: BackupConfig) -> None:
    create_backup(config, now=NOW)
    assert config.key_path.exists()
    cloud = config.cloud_dir.resolve()
    local = config.local_dir.resolve()
    assert config.key_path.resolve().parent not in (cloud, local)
    assert not any("key" in p.name.lower() for p in config.cloud_dir.iterdir())


def test_evidencija_zadnjeg_backupa(config: BackupConfig) -> None:
    create_backup(config, now=NOW)
    last = config.cloud_dir / LAST_BACKUP_FILENAME
    assert last.exists()
    assert NOW.isoformat() in last.read_text()


def test_restore_pogresnim_kljucem_dize_BackupError(config: BackupConfig, tmp_path: Path) -> None:
    enc = create_backup(config, now=NOW)
    config.key_path.write_bytes(Fernet.generate_key())  # drugi, validan ključ
    with pytest.raises(BackupError):
        restore_backup(config, enc, tmp_path / "restored.db")


def test_load_key_bez_kljuca_dize_BackupError(tmp_path: Path) -> None:
    with pytest.raises(BackupError):
        load_key(tmp_path / "nepostojeci.key")


def test_ensure_key_generise_i_persistira(tmp_path: Path) -> None:
    key_path = tmp_path / "k" / "backup.key"
    first = ensure_key(key_path)
    assert key_path.exists()
    assert ensure_key(key_path) == first


def test_backups_to_delete_zadrzava_dnevne_i_mjesecne() -> None:
    files = [
        Path("dentaland-2026-08-16.db.enc"),
        Path("dentaland-2026-08-15.db.enc"),
        Path("dentaland-2026-08-14.db.enc"),
        Path("dentaland-2026-07-31.db.enc"),
        Path("dentaland-2026-07-15.db.enc"),
        Path("dentaland-2026-07-01.db.enc"),
        Path("dentaland-2026-06-30.db.enc"),
        Path("dentaland-2026-06-01.db.enc"),
        Path("dentaland-2026-05-15.db.enc"),
    ]
    to_delete = _backups_to_delete(files, daily_keep=3, monthly_keep=2)
    kept = set(files) - to_delete

    assert Path("dentaland-2026-08-16.db.enc") in kept
    assert Path("dentaland-2026-08-15.db.enc") in kept
    assert Path("dentaland-2026-08-14.db.enc") in kept
    assert Path("dentaland-2026-07-31.db.enc") in kept  # najnoviji julski
    assert Path("dentaland-2026-06-30.db.enc") in kept  # najnoviji junski

    assert Path("dentaland-2026-07-15.db.enc") in to_delete
    assert Path("dentaland-2026-07-01.db.enc") in to_delete
    assert Path("dentaland-2026-06-01.db.enc") in to_delete
    assert Path("dentaland-2026-05-15.db.enc") in to_delete


def test_rotate_backups_brise_sa_diska(tmp_path: Path) -> None:
    cfg = BackupConfig(
        db_path=tmp_path / "x.db",
        local_dir=tmp_path / "local",
        cloud_dir=tmp_path / "cloud",
        key_path=tmp_path / "k.key",
        daily_keep=3,
        monthly_keep=1,
    )
    cfg.cloud_dir.mkdir(parents=True)
    names = [
        "dentaland-2026-08-16.db.enc",
        "dentaland-2026-08-15.db.enc",
        "dentaland-2026-08-14.db.enc",
        "dentaland-2026-07-31.db.enc",
        "dentaland-2026-07-15.db.enc",
    ]
    for name in names:
        (cfg.cloud_dir / name).write_bytes(b"x")

    deleted = rotate_backups(cfg)
    assert {p.name for p in deleted} == {"dentaland-2026-07-15.db.enc"}
    remaining = {p.name for p in cfg.cloud_dir.iterdir()}
    assert "dentaland-2026-07-15.db.enc" not in remaining
    assert "dentaland-2026-08-16.db.enc" in remaining
