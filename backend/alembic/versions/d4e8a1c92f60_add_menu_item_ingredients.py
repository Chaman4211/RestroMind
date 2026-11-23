"""Add ingredients to menu items."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e8a1c92f60"
down_revision: Union[str, Sequence[str], None] = "c8a41e72d901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "menu_items",
        sa.Column(
            "ingredients",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("menu_items", "ingredients")
