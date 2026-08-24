"""Centralne putanje za Dentaland — data/db/config/log/backup/resource.

Jedno mjesto koje definiše gdje aplikacija drži podatke i resurse, da
nijedan modul ne računa putanje sam (relativno prema cwd-u ili source
tree-u). Instalirana aplikacija koristi user data folder — na Windowsu
``%LOCALAPPDATA%/Dentaland`` — nikad Program Files (tamo obično nema
dozvolu za pisanje).

Dev vs prod odluka za BAZU (``dentaland.db`` iz cwd-a kad postoji, inače
``data_dir()``) je politika desktop entrypointa (``desktop/app.py``), NE
ovog modula — da ``database_path()`` ostane čista i da je testovi mogu
pouzdano override-ovati kroz ``DENTALAND_DATA_DIR``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

APP_DIR_NAME = "Dentaland"
DB_FILENAME = "dentaland.db"
ENV_DATA_DIR = "DENTALAND_DATA_DIR"
ENV_BACKUP_CLOUD_DIR = "DENTALAND_BACKUP_CLOUD_DIR"


def data_dir(env: Mapping[str, str] | None = None) -> Path:
    """User data folder aplikacije.

    Redoslijed:
    1. ``DENTALAND_DATA_DIR`` (eksplicitni override — testovi, portabilni dev);
    2. platform default: Windows ``%LOCALAPPDATA%/Dentaland``, macOS
       ``~/Library/Application Support/Dentaland``, Linux ``~/.local/share/dentaland``.
    """
    environ: Mapping[str, str] = os.environ if env is None else env
    override = environ.get(ENV_DATA_DIR)
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME.lower()


def database_path(env: Mapping[str, str] | None = None) -> Path:
    """Default put do baze: ``data_dir()/dentaland.db``."""
    return data_dir(env) / DB_FILENAME


def config_dir(env: Mapping[str, str] | None = None) -> Path:
    """Folder za konfiguracione fajlove."""
    return data_dir(env) / "config"


def log_dir(env: Mapping[str, str] | None = None) -> Path:
    """Folder za log fajlove."""
    return data_dir(env) / "logs"


def backup_dir(env: Mapping[str, str] | None = None) -> Path:
    """Folder za backup (vidi ``dentaland.backup.BackupConfig``)."""
    return data_dir(env) / "backups"


def backup_cloud_dir(env: Mapping[str, str] | None = None) -> Path:
    """Cloud/sync folder za backup (vidi ``DENTALAND_BACKUP_CLOUD_DIR``).

    Default je lokalni ``backup_dir()`` — radi odmah bez podešavanja. Ako je
    postavljena ``DENTALAND_BACKUP_CLOUD_DIR`` (npr. Google Drive/Dropbox sync
    folder), koristi se ta putanja.
    """
    environ: Mapping[str, str] = os.environ if env is None else env
    override = environ.get(ENV_BACKUP_CLOUD_DIR)
    if override:
        return Path(override).expanduser()
    return backup_dir(env)


def resource_path(*parts: str) -> Path:
    """Put do bundle-ovanog resursa (npr. ``web/assets/logo.png``).

    U source checkout-u resursi žive u ``web/`` ispod repo root-a. U
    PyInstaller bundle-u (budući DENT-IMPROVE-009) resursi su u
    ``sys._MEIPASS``.
    """
    bundle = getattr(sys, "_MEIPASS", None)
    base = Path(bundle) if bundle else Path(__file__).resolve().parents[2]
    return base.joinpath(*parts)
