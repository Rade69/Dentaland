"""Backup SQLite baze — SQLite backup API + enkripcija + rotacija.

Pravila (``CLAUDE.md`` / ``docs/dentaland-razvojni-plan-v3.1.md`` sekcija
"Backup mehanizam"):

- Backup ide isključivo kroz ``sqlite3.Connection.backup()`` — nikad sirovo
  kopiranje ``.db`` fajla (rizik WAL nekonzistentnosti pri otvorenoj bazi).
- Tok: lokalno plain ``.db`` (privremeno) → enkripcija → tek onda sync folder
  (Google Drive/Dropbox). Plain ``.db`` se briše odmah nakon enkripcije.
- Enkripcija: Fernet (``cryptography``) — simetrična, autentifikovana
  (tamper-evident: pogrešan ključ ili izmenjen fajl → ``BackupError``).
- Ključ za dekripciju se čuva ODVOJENO od backup foldera.
- Rotacija: zadrži ``daily_keep`` najnovijih dnevnih + po jedan (najnoviji)
  mjesečni backup za ``monthly_keep`` prethodnih mjeseci; ostalo briše.

Fernet učitava ceo fajl u memoriju — prihvatljivo za ordinacijsku bazu
(reda MB–desetine MB), ne za streaming velikih fajlova.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

LAST_BACKUP_FILENAME = "last_backup.txt"
BACKUP_PREFIX = "dentaland-"
BACKUP_SUFFIX = ".db.enc"


class BackupError(Exception):
    """Greška pri backupu ili restore-u."""


@dataclass
class BackupConfig:
    """Putevi i pravila rotacije za backup.

    ``key_path`` mora biti izvan ``local_dir`` i ``cloud_dir`` — ključ se ne
    smije naći u istom folderu kao backup.
    """

    db_path: Path
    local_dir: Path
    cloud_dir: Path
    key_path: Path
    daily_keep: int = 30
    monthly_keep: int = 3


def ensure_key(key_path: Path) -> bytes:
    """Vrati enkripcijski ključ; generiši i sačuvaj ako još ne postoji."""
    if key_path.exists():
        return load_key(key_path)
    key = Fernet.generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    return key


def load_key(key_path: Path) -> bytes:
    """Učitaj postojeći ključ; greška ako ne postoji (koristi se za restore)."""
    if not key_path.exists():
        raise BackupError(f"Ključ ne postoji: {key_path}")
    return key_path.read_bytes()


def backup_database(source_path: Path, dest_path: Path) -> None:
    """Konzistentna kopija baze kroz SQLite online backup API.

    Radi i dok je izvorna baza otvorena (za razliku od sirovog kopiranja).
    """
    src = sqlite3.connect(str(source_path))
    dst = sqlite3.connect(str(dest_path))
    try:
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()


def _encrypt(plain_path: Path, enc_path: Path, key: bytes) -> None:
    enc_path.write_bytes(Fernet(key).encrypt(plain_path.read_bytes()))


def _decrypt(enc_path: Path, plain_path: Path, key: bytes) -> None:
    try:
        data = Fernet(key).decrypt(enc_path.read_bytes())
    except InvalidToken as exc:
        raise BackupError(f"Neispravan ključ ili oštećen backup: {enc_path}") from exc
    plain_path.write_bytes(data)


def _backup_filename(now: datetime) -> str:
    return f"{BACKUP_PREFIX}{now:%Y-%m-%d}{BACKUP_SUFFIX}"


def _month_of(path: Path) -> str | None:
    """Izdvoji ``YYYY-MM`` iz imena backupa, ili ``None`` ako ne odgovara šemi."""
    name = path.name
    if not name.startswith(BACKUP_PREFIX) or not name.endswith(BACKUP_SUFFIX):
        return None
    body = name[len(BACKUP_PREFIX) : -len(BACKUP_SUFFIX)]
    parts = body.split("-")
    if len(parts) != 3:
        return None
    return "-".join(parts[:2])


def _list_backups(cloud_dir: Path) -> list[Path]:
    # Imena sadrže zero-padded datum → leksikografski sort = hronološki.
    return sorted(cloud_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"), reverse=True)


def _backups_to_delete(files: list[Path], daily_keep: int, monthly_keep: int) -> set[Path]:
    """Odredi koje backup fajlove rotacija briše (čista logika, bez diska).

    ``files`` mora biti sortiran od najnovijeg ka najstarijem.
    """
    keep: set[Path] = set(files[:daily_keep])

    monthly: dict[str, Path] = {}
    for path in files[daily_keep:]:
        month = _month_of(path)
        if month is None:
            keep.add(path)  # ne prepoznajemo ime — ne diraj
            continue
        monthly.setdefault(month, path)  # prvi = najnoviji u tom mjesecu

    kept_months = sorted(monthly, reverse=True)[:monthly_keep]
    keep.update(monthly[m] for m in kept_months)
    return set(files) - keep


def rotate_backups(config: BackupConfig) -> list[Path]:
    """Obriši stare backupe po pravilu rotacije; vrati listu obrisanih."""
    files = _list_backups(config.cloud_dir)
    to_delete = _backups_to_delete(files, config.daily_keep, config.monthly_keep)
    deleted: list[Path] = []
    for path in to_delete:
        path.unlink(missing_ok=True)
        deleted.append(path)
    return deleted


def _write_last_backup(cloud_dir: Path, when: datetime) -> None:
    (cloud_dir / LAST_BACKUP_FILENAME).write_text(when.isoformat() + "\n")


def create_backup(config: BackupConfig, now: datetime | None = None) -> Path:
    """Napravi dnevni backup i vrati putanju enkriptovanog fajla.

    Poziva se iz schedulera (sam scheduler nije dio ovog modula).
    """
    now = now or datetime.now().astimezone()
    config.local_dir.mkdir(parents=True, exist_ok=True)
    config.cloud_dir.mkdir(parents=True, exist_ok=True)

    key = ensure_key(config.key_path)
    local_tmp = config.local_dir / "backup-tmp.db"
    try:
        backup_database(config.db_path, local_tmp)
        enc_path = config.cloud_dir / _backup_filename(now)
        _encrypt(local_tmp, enc_path, key)
    finally:
        # Plain .db je samo privremeni lokalni korak — nikad ne ostaje.
        local_tmp.unlink(missing_ok=True)

    rotate_backups(config)
    _write_last_backup(config.cloud_dir, now)
    return enc_path


def restore_backup(config: BackupConfig, enc_path: Path, dest_path: Path) -> None:
    """Dekriptuj backup u plain ``.db`` na ``dest_path``."""
    key = load_key(config.key_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    _decrypt(enc_path, dest_path, key)
