"""Add upload-specific table zones."""

from alembic import op
import sqlalchemy as sa

revision = "a71d8e4c9f20"
down_revision = "c3d9a7f12b40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurant_tables",
        sa.Column("upload_zone_coordinates", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurant_tables", "upload_zone_coordinates")
