"""Add cancellation details to restaurant orders."""

from alembic import op
import sqlalchemy as sa

revision = "c7d9e2f4a610"
down_revision = "b82d7e4a91c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurant_orders",
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "restaurant_orders",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurant_orders", "cancelled_at")
    op.drop_column("restaurant_orders", "cancellation_reason")
