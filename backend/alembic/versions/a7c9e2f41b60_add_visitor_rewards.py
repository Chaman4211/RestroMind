"""Add anonymous visitor-based daily rewards."""

import sqlalchemy as sa

from alembic import op

revision = "a7c9e2f41b60"
down_revision = "d4e8f2a9b731"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visitor_reward_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("visitor_id", sa.String(length=36), nullable=False),
        sa.Column(
            "points",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "visitor_id",
            name="uq_visitor_reward_accounts_visitor_id",
        ),
    )
    op.create_index(
        "ix_visitor_reward_accounts_visitor_id",
        "visitor_reward_accounts",
        ["visitor_id"],
    )

    op.create_table(
        "visitor_reward_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("visitor_id", sa.String(length=36), nullable=False),
        sa.Column(
            "table_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("challenge_date", sa.Date(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column(
            "points_awarded",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "visitor_id",
            "challenge_date",
            name="uq_visitor_reward_daily_challenge",
        ),
    )
    op.create_index(
        "ix_visitor_reward_claims_visitor_id",
        "visitor_reward_claims",
        ["visitor_id"],
    )
    op.create_index(
        "ix_visitor_reward_claims_table_id",
        "visitor_reward_claims",
        ["table_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_visitor_reward_claims_table_id",
        table_name="visitor_reward_claims",
    )
    op.drop_index(
        "ix_visitor_reward_claims_visitor_id",
        table_name="visitor_reward_claims",
    )
    op.drop_table("visitor_reward_claims")
    op.drop_index(
        "ix_visitor_reward_accounts_visitor_id",
        table_name="visitor_reward_accounts",
    )
    op.drop_table("visitor_reward_accounts")
