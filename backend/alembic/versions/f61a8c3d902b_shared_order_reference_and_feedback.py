"""add shared order reference and customer feedback

Revision ID: f61a8c3d902b
Revises: e4f8b2c91a60
"""
from alembic import op
import sqlalchemy as sa

revision = "f61a8c3d902b"
down_revision = "e4f8b2c91a60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "table_order_sessions",
        sa.Column("last_order_token", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "table_order_sessions",
        sa.Column("last_order_round", sa.Integer(), nullable=True),
    )
    op.create_table(
        "restaurant_order_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("order_id", name="uq_order_feedback_order_id"),
    )
    op.create_index(
        "ix_restaurant_order_feedback_order_id",
        "restaurant_order_feedback",
        ["order_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_restaurant_order_feedback_order_id",
        table_name="restaurant_order_feedback",
    )
    op.drop_table("restaurant_order_feedback")
    op.drop_column("table_order_sessions", "last_order_round")
    op.drop_column("table_order_sessions", "last_order_token")
