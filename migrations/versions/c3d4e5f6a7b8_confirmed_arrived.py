"""DENT-012 — confirmed_at/arrived_at na appointments.

Aditivne nullable kolone, nezavisne od status enuma — vidi
docstring uz Appointment.confirmed_at/arrived_at u
``src/dentaland/models.py`` i ``agent_reports/2026-08-17-DENT-012-plan.md``
za odbačenu alternativu (proširenje AppointmentStatus enuma).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appointments", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("confirmed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("arrived_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("appointments", recreate="always") as batch_op:
        batch_op.drop_column("arrived_at")
        batch_op.drop_column("confirmed_at")
