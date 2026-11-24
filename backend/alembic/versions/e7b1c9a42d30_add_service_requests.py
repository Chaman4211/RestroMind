"""Add customer service requests."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e7b1c9a42d30"
down_revision: str | Sequence[str] | None = "d4e8a1c92f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "table_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_type", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.Column(
            "handled_by_staff_id",
            sa.Integer(),
            sa.ForeignKey("staff_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_service_requests_table_id",
        "service_requests",
        ["table_id"],
    )
    op.create_index(
        "ix_service_requests_status",
        "service_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_service_requests_status", table_name="service_requests")
    op.drop_index("ix_service_requests_table_id", table_name="service_requests")
    op.drop_table("service_requests")
