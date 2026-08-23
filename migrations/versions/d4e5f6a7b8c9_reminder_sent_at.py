"""DENT-022 — reminder_sent_at na appointments.

Aditivna nullable kolona — dedup oznaka za email podsjetnik (DENT-020).
NULL = podsjetnik nije poslan. Vidi docstring uz
Appointment.reminder_sent_at u ``src/dentaland/models.py`` i
``agent_reports/2026-08-23-DENT-022-plan.md``.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appointments", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("reminder_sent_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("appointments", recreate="always") as batch_op:
        batch_op.drop_column("reminder_sent_at")
