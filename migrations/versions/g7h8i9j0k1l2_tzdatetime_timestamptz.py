"""DENT-IMPROVE-019 — TZDateTime kolone postaju stvarno timestamptz.

Root cause i puno objašnjenje:
agent_reports/DENT-IMPROVE-019-task-contract.md. Ukratko: sve
``TZDateTime`` kolone su do sada bile ``timestamp without time zone`` na
Postgresu. Postgres pri upisu tz-aware vrijednosti u takvu kolonu prvo
konvertuje u sesijsku ``TimeZone`` (server default) PA TEK ONDA odbaci
oznaku zone — tiho pomjera upisano vrijeme za offset servera na svakom
serveru čija sesijska zona nije UTC.

Namjerno NE koristi ``op.batch_alter_table(..., recreate="always")``
(obrazac iz ranijih migracija) — to na Postgresu radi preko privremene
tabele i RESETUJE SERIAL sekvence (stvarno pogođeno tokom
DENT-IMPROVE-018 test VPS deploya, vidi CURRENT_STATE.md), što bi za
ovu migraciju pogodilo VIŠE tabela odjednom. Umjesto toga: direktan
``ALTER COLUMN ... TYPE timestamptz USING ... AT TIME ZONE 'UTC'`` na
Postgresu (bez rekreacije tabele, sekvence netaknute), no-op na SQLite
(nema stvarnu timestamptz/timestamp razliku — deklarisani tip se mijenja
samo na Python/SQLAlchemy nivou, ništa se ne upisuje u SQLite fajl
drugačije).

``USING <col> AT TIME ZONE 'UTC'`` tretira POSTOJEĆU naivnu vrijednost
kao da već JESTE UTC — najbolja moguća pretpostavka bez pravih
podataka za oporavak (hosting/produkcijska odluka je i dalje odgođena,
vidi CLAUDE.md "Otvorena pitanja" — nijedan Postgres server sa stvarnim
pacijentskim podacima još ne postoji).

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g7h8i9j0k1l2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (tabela, kolona) za sve TZDateTime kolone koje postoje na ovom lancu
# migracija (glavna grana — DENT-IMPROVE-018 telegram_* kolone se
# dodaju posebnom migracijom i nasljeđuju ispravan tip direktno kroz
# ažurirani TZDateTime, ne trebaju ovdje).
_TZDATETIME_COLUMNS: list[tuple[str, str]] = [
    ("time_off", "od_datetime"),
    ("time_off", "do_datetime"),
    ("appointments", "start_time"),
    ("appointments", "end_time"),
    ("appointments", "confirmed_at"),
    ("appointments", "arrived_at"),
    ("appointments", "reminder_sent_at"),
    ("appointments", "created_at"),
    ("appointments", "updated_at"),
    ("users", "created_at"),
    ("sessions", "expires_at"),
    ("sessions", "created_at"),
    ("sessions", "revoked_at"),
    ("audit_events", "occurred_at"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (i svaki drugi dijalekt bez stvarne timestamptz/timestamp
        # razlike u skladištu) — deklarisani tip se mijenja samo na
        # Python/SQLAlchemy nivou, nema DDL efekta koji treba primijeniti.
        return
    for table, column in _TZDATETIME_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column in _TZDATETIME_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=False),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
