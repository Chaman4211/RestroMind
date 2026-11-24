"""add restaurant wifi settings

Revision ID: a72c9e51d4b8
Revises: f61a8c3d902b
"""

import sqlalchemy as sa

from alembic import op

revision = "a72c9e51d4b8"
down_revision = "f61a8c3d902b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wifi_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ssid", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("password_encrypted", sa.String(length=500), nullable=True),
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("wifi_settings")
