"""Associate upload table zones with their upload source."""

from alembic import op
import sqlalchemy as sa

revision = "b82d7e4a91c3"
down_revision = "a71d8e4c9f20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurant_tables",
        sa.Column("upload_camera_source_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_restaurant_tables_upload_camera_source_id",
        "restaurant_tables",
        "camera_sources",
        ["upload_camera_source_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_restaurant_tables_upload_camera_source_id",
        "restaurant_tables",
        type_="foreignkey",
    )
    op.drop_column("restaurant_tables", "upload_camera_source_id")
