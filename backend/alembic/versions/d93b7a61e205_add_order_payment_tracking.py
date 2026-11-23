"""Add order payment tracking and link bill requests to orders.

Revision ID: d93b7a61e205
Revises: a61e9c7b42d0
"""
from alembic import op
import sqlalchemy as sa

revision = "d93b7a61e205"
down_revision = "a61e9c7b42d0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("restaurant_orders", sa.Column("payment_method", sa.String(40), nullable=True))
    op.add_column("restaurant_orders", sa.Column("payment_provider", sa.String(60), nullable=True))
    op.add_column(
        "restaurant_orders",
        sa.Column("payment_status", sa.String(20), server_default="UNPAID", nullable=False),
    )
    op.add_column("restaurant_orders", sa.Column("payment_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("restaurant_orders", sa.Column("payment_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_requests", sa.Column("order_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_service_requests_order_id", "service_requests", "restaurant_orders",
        ["order_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_service_requests_order_id", "service_requests", ["order_id"])


def downgrade():
    op.drop_index("ix_service_requests_order_id", table_name="service_requests")
    op.drop_constraint("fk_service_requests_order_id", "service_requests", type_="foreignkey")
    op.drop_column("service_requests", "order_id")
    op.drop_column("restaurant_orders", "payment_confirmed_at")
    op.drop_column("restaurant_orders", "payment_requested_at")
    op.drop_column("restaurant_orders", "payment_status")
    op.drop_column("restaurant_orders", "payment_provider")
    op.drop_column("restaurant_orders", "payment_method")
