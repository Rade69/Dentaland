from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Dodaj src/ na sys.path da bi se dentaland.models mogao importovati iz env.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dentaland.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DENT-IMPROVE-012: DATABASE_URL env var ima prednost nad alembic.ini
# vrijednošću (standardni Alembic obrazac) — omogućava alembic upgrade nad
# PostgreSQL bez diranja sqlite default-a u alembic.ini (desktop Faza 0
# nastavlja da radi bez env varijable).
#
# `%` mora biti escapovan kao `%%` prije `set_main_option` — Alembicov
# `Config` čuva vrijednosti kroz `ConfigParser` sa uključenom interpolacijom,
# pa bi validan URL-encoded znak u kredencijalima (npr. lozinka sa `%25`)
# inače izazvao `ValueError: invalid interpolation syntax` PRIJE ijednog
# pokušaja konekcije (Codex review F1, DENT-IMPROVE-012).
#
# Override se primjenjuje SAMO ako `config` još uvijek ima neizmijenjen
# alembic.ini default (`sqlite:///dentaland.db`) -- ako je pozivalac (npr.
# postojeći `tests/test_models.py`/`test_requests.py`, koji programski prave
# svoj `Config("alembic.ini")` i eksplicitno zovu `set_main_option` na
# izolovanu tmp SQLite bazu PRIJE `command.upgrade(config, ...)`) već
# eksplicitno postavio drugačiji URL, taj izbor se poštuje i NE pregazi.
# Bez ovoga, bilo koji proces sa `DATABASE_URL` u okruženju bi tiho slao te
# testove protiv Postgres umjesto njihove namjeravane izolovane SQLite baze
# (Pi review, DENT-IMPROVE-012 -- reprodukovano: 4 testa padaju sa
# `NoSuchTableError` jer `command.upgrade` ode na Postgres dok test poslije
# gleda praznu SQLite datoteku).
_ALEMBIC_INI_DEFAULT_URL = "sqlite:///dentaland.db"
_database_url = os.environ.get("DATABASE_URL")
if _database_url and config.get_main_option("sqlalchemy.url") == _ALEMBIC_INI_DEFAULT_URL:
    config.set_main_option("sqlalchemy.url", _database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Pokreni migracije u offline modu (bez DBAPI konekcije)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Pokreni migracije u online modu (kroz SQLAlchemy engine)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
