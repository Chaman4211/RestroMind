"""Add table-based daily rewards.

Revision ID: 9a4c2d7e1b60
Revises: f3a9d6c21b70
"""
import sqlalchemy as sa

from alembic import op

revision = "9a4c2d7e1b60"
down_revision = "f3a9d6c21b70"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reward_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "table_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("points", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("table_id", name="uq_reward_accounts_table_id"),
    )
    op.create_index(
        "ix_reward_accounts_table_id", "reward_accounts", ["table_id"]
    )

    op.create_table(
        "reward_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "table_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("challenge_date", sa.Date(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("points_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "table_id",
            "challenge_date",
            name="uq_reward_table_daily_challenge",
        ),
    )
    op.create_index("ix_reward_claims_table_id", "reward_claims", ["table_id"])


def downgrade():
    op.drop_index("ix_reward_claims_table_id", table_name="reward_claims")
    op.drop_table("reward_claims")
    op.drop_index("ix_reward_accounts_table_id", table_name="reward_accounts")
    op.drop_table("reward_accounts")
