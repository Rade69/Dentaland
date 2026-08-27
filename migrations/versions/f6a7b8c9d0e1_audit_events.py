"""DENT-IMPROVE-014 — audit_events tabela (append-only audit log, jezgro).

Šema po v3.1 planu, sekcija "Audit log" (oko linije 267): id,
actor_user_id, action, resource_type, resource_id, occurred_at,
request_id, source_ip, metadata_minimal. Akcije su tačno backlog
"Minimum events" lista (7 vrijednosti) — vidi docstring uz `AuditAction`
u `src/dentaland/models.py`.

Bez instrumentacije stvarnih poziva u ovom tasku (to rade
DENT-IMPROVE-014B/014C paralelno, poslije merge-a) — vidi
`src/dentaland/services/audit.py`.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "LOGIN_SUCCESS",
                "LOGIN_FAILURE",
                "CREATE_APPOINTMENT",
                "UPDATE_APPOINTMENT",
                "CANCEL_APPOINTMENT",
                "DELETE_APPOINTMENT",
                "CHANGE_ROLE",
                name="audit_action",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("metadata_minimal", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
