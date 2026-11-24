"""Add menu size prices and selected size to order items."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3a9d6c21b70"
down_revision: str | Sequence[str] | None = "e7b1c9a42d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "menu_items",
        sa.Column(
            "size_prices",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
    )
    op.add_column(
        "order_items",
        sa.Column("size", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_items", "size")
    op.drop_column("menu_items", "size_prices")
