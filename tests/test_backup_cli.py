"""Testovi za operativni backup CLI (DENT-IMPROVE-007)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from dentaland.backup import BACKUP_PREFIX, BACKUP_SUFFIX, LAST_BACKUP_FILENAME
from dentaland.backup_cli import main


def _seed_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE appointments (id INTEGER PRIMARY KEY, ime TEXT)")
    conn.execute("INSERT INTO appointments (id, ime) VALUES (1, 'Pacijent')")
    conn.commit()
    conn.close()


def _appointment_count(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    finally:
        conn.close()


def test_run_kreira_enkriptovan_backup(tmp_path: Path) -> None:
    env = {"DENTALAND_DATA_DIR": str(tmp_path)}
    _seed_db(tmp_path / "dentaland.db")

    result = main(["run"], env=env)

    assert result == 0
    cloud = tmp_path / "backups"
    encs = list(cloud.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))
    assert len(encs) == 1
    assert not any(p.suffix == ".db" for p in cloud.iterdir())
    # Ključ mora biti van backup foldera (config_dir, ne backups).
    key = tmp_path / "config" / "backup.key"
    assert key.exists()
    assert key.parent.resolve() != cloud.resolve()


def test_run_cloud_override_iz_env(tmp_path: Path) -> None:
    cloud_sync = tmp_path / "cloud-sync"
    env = {
        "DENTALAND_DATA_DIR": str(tmp_path),
        "DENTALAND_BACKUP_CLOUD_DIR": str(cloud_sync),
    }
    _seed_db(tmp_path / "dentaland.db")

    result = main(["run"], env=env)

    assert result == 0
    assert any(cloud_sync.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))
    assert not any(p.suffix == ".db" for p in cloud_sync.iterdir())


def test_run_failure_nenula_exit(tmp_path: Path) -> None:
    env = {"DENTALAND_DATA_DIR": str(tmp_path)}
    # Direktorijum na mjestu baze → sqlite3.connect baca (realan failure, ne mock).
    (tmp_path / "dentaland.db").mkdir()

    result = main(["run"], env=env)

    assert result == 1


def test_restore_test_prolazi_na_zasebnoj_destinaciji(tmp_path: Path) -> None:
    env = {"DENTALAND_DATA_DIR": str(tmp_path)}
    _seed_db(tmp_path / "dentaland.db")
    assert main(["run"], env=env) == 0

    result = main(["restore-test"], env=env)

    assert result == 0
    # Plain test .db je obrisan — ne ostaje plaintext.
    assert not (tmp_path / "restore-test" / "dentaland-test.db").exists()
    # Aktivna baza netaknuta.
    assert _appointment_count(tmp_path / "dentaland.db") == 1


def test_restore_test_bez_backupa_nenula_exit(tmp_path: Path) -> None:
    env = {"DENTALAND_DATA_DIR": str(tmp_path)}
    _seed_db(tmp_path / "dentaland.db")

    result = main(["restore-test"], env=env)

    assert result == 1


def test_restore_test_korumpiran_backup_nenula_exit(tmp_path: Path) -> None:
    env = {"DENTALAND_DATA_DIR": str(tmp_path)}
    _seed_db(tmp_path / "dentaland.db")
    assert main(["run"], env=env) == 0
    enc = next((tmp_path / "backups").glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))
    enc.write_bytes(b"korumpiran")  # Fernet.decrypt → InvalidToken → BackupError

    result = main(["restore-test"], env=env)

    assert result == 1
    assert not (tmp_path / "restore-test" / "dentaland-test.db").exists()


def test_status_bez_evidencije(tmp_path: Path, capsys) -> None:
    env = {"DENTALAND_DATA_DIR": str(tmp_path)}

    result = main(["status"], env=env)

    assert result == 0
    assert "Nema evidencije" in capsys.readouterr().out


def test_status_svjez_backup(tmp_path: Path, capsys) -> None:
    env = {"DENTALAND_DATA_DIR": str(tmp_path)}
    _seed_db(tmp_path / "dentaland.db")
    assert main(["run"], env=env) == 0

    result = main(["status"], env=env)

    out = capsys.readouterr().out
    assert result == 0
    assert "OK" in out
    assert "STARO" not in out


def test_status_star_backup(tmp_path: Path, capsys) -> None:
    env = {"DENTALAND_DATA_DIR": str(tmp_path)}
    cloud = tmp_path / "backups"
    cloud.mkdir(parents=True)
    old = datetime.now().astimezone() - timedelta(hours=30)
    (cloud / LAST_BACKUP_FILENAME).write_text(old.isoformat() + "\n")

    result = main(["status"], env=env)

    out = capsys.readouterr().out
    assert result == 0
    assert "STARO" in out
