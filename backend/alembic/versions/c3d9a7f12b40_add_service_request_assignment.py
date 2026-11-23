
"""Add service request staff assignment."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d9a7f12b40"
down_revision: Union[str, Sequence[str], None] = "a72c9e51d4b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_requests",
        sa.Column("assigned_staff_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_service_requests_assigned_staff_id",
        "service_requests",
        "staff_users",
        ["assigned_staff_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_service_requests_assigned_staff_id",
        "service_requests",
        ["assigned_staff_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_service_requests_assigned_staff_id",
        table_name="service_requests",
    )
    op.drop_constraint(
        "fk_service_requests_assigned_staff_id",
        "service_requests",
        type_="foreignkey",
    )
    op.drop_column("service_requests", "assigned_staff_id")
