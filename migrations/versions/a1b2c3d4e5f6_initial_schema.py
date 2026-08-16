"""Initial schema — Faza 0 tabele.

Tabele doctors/services/working_hours/time_off/appointments, tačno prema
``docs/dentaland-razvojni-plan-v3.1.md`` (sekcija "Faza 0 — Šema baze").

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ime", sa.String(length=200), nullable=False),
        sa.Column("aktivan", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("naziv", sa.String(length=200), nullable=False),
        sa.Column("trajanje_min", sa.Integer(), nullable=False),
        sa.Column("buffer_min", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "working_hours",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("dan_u_sedmici", sa.Integer(), nullable=False),
        sa.Column("od_local", sa.Time(), nullable=False),
        sa.Column("do_local", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "time_off",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("od_datetime", sa.DateTime(), nullable=False),
        sa.Column("do_datetime", sa.DateTime(), nullable=False),
        sa.Column("razlog", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("ime", sa.String(length=200), nullable=False),
        sa.Column("telefon", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("napomena", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "SCHEDULED",
                "CANCELLED",
                "COMPLETED",
                "NO_SHOW",
                name="appointment_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_manual_override",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("appointments")
    op.drop_table("time_off")
    op.drop_table("working_hours")
    op.drop_table("services")
    op.drop_table("doctors")
