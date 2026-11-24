"""Add customer suggestions to order feedback."""

from alembic import op
import sqlalchemy as sa

revision = "d4e8f2a9b731"
down_revision = "c7d9e2f4a610"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurant_order_feedback",
        sa.Column("suggestion", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurant_order_feedback", "suggestion")
