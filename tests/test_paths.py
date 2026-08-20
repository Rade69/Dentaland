"""Testovi za centralne putanje (DENT-IMPROVE-003)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dentaland import paths


def test_data_dir_postuje_override() -> None:
    assert paths.data_dir({"DENTALAND_DATA_DIR": "/tmp/dentaland-data"}) == Path(
        "/tmp/dentaland-data"
    )


def test_data_dir_default_windows_localappdata() -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only grana")
    assert paths.data_dir({"LOCALAPPDATA": "C:/Users/u/AppData/Local"}) == Path(
        "C:/Users/u/AppData/Local/Dentaland"
    )


def test_database_path_pod_data_dir() -> None:
    assert paths.database_path({"DENTALAND_DATA_DIR": "/tmp/x"}) == Path("/tmp/x") / "dentaland.db"


def test_poddirektorijumi_pod_data_dir() -> None:
    env = {"DENTALAND_DATA_DIR": "/tmp/x"}
    assert paths.config_dir(env) == Path("/tmp/x") / "config"
    assert paths.log_dir(env) == Path("/tmp/x") / "logs"
    assert paths.backup_dir(env) == Path("/tmp/x") / "backups"


def test_resource_path_pokazuje_na_postojeci_logo() -> None:
    logo = paths.resource_path("web", "assets", "logo.png")
    assert logo.is_file()
