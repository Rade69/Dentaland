"""Faza 1 (priprema) — PENDING/REJECTED status, nullable polja za javne zahtjeve.

Aditivna dopuna najavljena od Faze 0 (vidi docstring AppointmentStatus u
``src/dentaland/models.py``): javni zahtjev sa web forme stiže bez doktora/
usluge/tačnog vremena (bira ih osoblje pri potvrdi), pa te kolone postaju
nullable, uz novo ``requested_date`` polje (datum koji je pacijent tražio).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_STATUSES = ("SCHEDULED", "CANCELLED", "COMPLETED", "NO_SHOW")
_NEW_STATUSES = ("SCHEDULED", "CANCELLED", "COMPLETED", "NO_SHOW", "PENDING", "REJECTED")


def upgrade() -> None:
    with op.batch_alter_table("appointments", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("requested_date", sa.Date(), nullable=True))
        batch_op.alter_column("doctor_id", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("service_id", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("start_time", existing_type=sa.DateTime(), nullable=True)
        batch_op.alter_column("end_time", existing_type=sa.DateTime(), nullable=True)
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                *_OLD_STATUSES,
                name="appointment_status",
                native_enum=False,
                create_constraint=True,
            ),
            type_=sa.Enum(
                *_NEW_STATUSES,
                name="appointment_status",
                native_enum=False,
                create_constraint=True,
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("appointments", recreate="always") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                *_NEW_STATUSES,
                name="appointment_status",
                native_enum=False,
                create_constraint=True,
            ),
            type_=sa.Enum(
                *_OLD_STATUSES,
                name="appointment_status",
                native_enum=False,
                create_constraint=True,
            ),
            existing_nullable=False,
        )
        batch_op.alter_column("end_time", existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column("start_time", existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column("service_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("doctor_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("requested_date")
