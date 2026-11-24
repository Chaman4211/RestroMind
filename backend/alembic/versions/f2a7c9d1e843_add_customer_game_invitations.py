"""Add customer game invitations and player presence."""

import sqlalchemy as sa

from alembic import op

revision = "f2a7c9d1e843"
down_revision = "c4d8a1b7e932"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "game_player_presence",
        sa.Column("visitor_id", sa.String(length=36), primary_key=True),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "game_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.String(length=36), nullable=False),
        sa.Column("receiver_id", sa.String(length=36), nullable=False),
        sa.Column("sender_table_id", sa.Integer(), nullable=False),
        sa.Column("receiver_table_id", sa.Integer(), nullable=False),
        sa.Column("game_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("room_code", sa.String(length=8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_game_invitations_sender_id",
        "game_invitations",
        ["sender_id"],
    )
    op.create_index(
        "ix_game_invitations_receiver_id",
        "game_invitations",
        ["receiver_id"],
    )
    op.create_index(
        "ix_game_invitations_status",
        "game_invitations",
        ["status"],
    )


def downgrade():
    op.drop_index("ix_game_invitations_status", table_name="game_invitations")
    op.drop_index("ix_game_invitations_receiver_id", table_name="game_invitations")
    op.drop_index("ix_game_invitations_sender_id", table_name="game_invitations")
    op.drop_table("game_invitations")
    op.drop_table("game_player_presence")
