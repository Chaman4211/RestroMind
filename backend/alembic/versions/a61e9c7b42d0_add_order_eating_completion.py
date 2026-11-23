"""Add customer eating completion timestamp to orders.

Revision ID: a61e9c7b42d0
Revises: 9a4c2d7e1b60
"""
from alembic import op
import sqlalchemy as sa

revision = "a61e9c7b42d0"
down_revision = "9a4c2d7e1b60"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "restaurant_orders",
        sa.Column("eating_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("restaurant_orders", "eating_completed_at")
