"""Add multiplayer game rooms."""

import sqlalchemy as sa

from alembic import op

revision = "c4d8a1b7e932"
down_revision = "a7c9e2f41b60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_code", sa.String(length=8), nullable=False),
        sa.Column("game_type", sa.String(length=30), nullable=False),
        sa.Column("board", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current_turn", sa.String(length=1), nullable=True),
        sa.Column("winner", sa.String(length=1), nullable=True),
        sa.Column("player_x_id", sa.String(length=36), nullable=False),
        sa.Column("player_o_id", sa.String(length=36), nullable=True),
        sa.Column("player_x_table_id", sa.Integer(), nullable=False),
        sa.Column("player_o_table_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("room_code", name="uq_game_rooms_room_code"),
    )
    op.create_index(
        "ix_game_rooms_room_code", "game_rooms", ["room_code"]
    )


def downgrade() -> None:
    op.drop_index("ix_game_rooms_room_code", table_name="game_rooms")
    op.drop_table("game_rooms")
