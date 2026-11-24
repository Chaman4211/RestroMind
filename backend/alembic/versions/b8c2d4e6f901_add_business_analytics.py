"""Add restaurant profile and payment transaction reference."""

import sqlalchemy as sa

from alembic import op

revision = "b8c2d4e6f901"
down_revision = "f2a7c9d1e843"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "restaurant_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "restaurant_name",
            sa.String(length=150),
            nullable=False,
            server_default="My Restaurant",
        ),
        sa.Column(
            "currency",
            sa.String(length=10),
            nullable=False,
            server_default="PKR",
        ),
    )
    op.add_column(
        "restaurant_orders",
        sa.Column("transaction_reference", sa.String(length=120), nullable=True),
    )


def downgrade():
    op.drop_column("restaurant_orders", "transaction_reference")
    op.drop_table("restaurant_profiles")
