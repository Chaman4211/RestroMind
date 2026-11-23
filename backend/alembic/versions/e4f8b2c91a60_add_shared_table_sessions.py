"""add shared table ordering sessions

Revision ID: e4f8b2c91a60
Revises: d93b7a61e205
"""
from alembic import op
import sqlalchemy as sa

revision = "e4f8b2c91a60"
down_revision = "d93b7a61e205"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "table_order_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "table_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("cart", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("table_order_sessions")
