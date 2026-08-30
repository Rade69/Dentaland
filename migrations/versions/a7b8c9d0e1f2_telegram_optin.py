"""DENT-IMPROVE-018 — Telegram opt-in polja na appointments.

Aditivne nullable kolone. telegram_link_token_hash/expires_at su
uže-namjenski jednokratni token (isti obrazac kao Session.token_hash,
DENT-IMPROVE-013) za /start deep link; brišu se nakon uspješne upotrebe.
telegram_chat_id/subscribed_at se popunjavaju TEK kad pacijent stvarno
klikne link i pošalje /start botu. Vidi docstring uz Appointment polja u
src/dentaland/models.py i src/dentaland/services/telegram.py.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appointments", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("telegram_link_token_hash", sa.String(64), nullable=True))
        batch_op.add_column(
            sa.Column("telegram_link_token_expires_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(sa.Column("telegram_chat_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("telegram_subscribed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("appointments", recreate="always") as batch_op:
        batch_op.drop_column("telegram_subscribed_at")
        batch_op.drop_column("telegram_chat_id")
        batch_op.drop_column("telegram_link_token_expires_at")
        batch_op.drop_column("telegram_link_token_hash")
