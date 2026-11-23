"""Add staff profiles and cleaning alert assignments."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c4e9a21d63"
down_revision: Union[str, Sequence[str], None] = "41d012558291"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "staff_users",
        sa.Column("name", sa.String(length=150), nullable=True),
    )
    op.add_column(
        "staff_users",
        sa.Column("email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "staff_users",
        sa.Column("phone", sa.String(length=30), nullable=True),
    )

    op.execute(
        "UPDATE staff_users SET name = COALESCE(username, 'Staff ' || id::text) "
        "WHERE name IS NULL"
    )

    op.alter_column(
        "staff_users",
        "name",
        existing_type=sa.String(length=150),
        nullable=False,
    )
    op.alter_column(
        "staff_users",
        "username",
        existing_type=sa.String(length=100),
        nullable=True,
    )
    op.alter_column(
        "staff_users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    op.create_index(
        "ix_staff_users_email",
        "staff_users",
        ["email"],
        unique=True,
    )

    op.add_column(
        "alerts",
        sa.Column("assigned_staff_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_alerts_assigned_staff_id",
        "alerts",
        ["assigned_staff_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_alerts_assigned_staff_id_staff_users",
        "alerts",
        "staff_users",
        ["assigned_staff_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_alerts_assigned_staff_id_staff_users",
        "alerts",
        type_="foreignkey",
    )
    op.drop_index("ix_alerts_assigned_staff_id", table_name="alerts")
    op.drop_column("alerts", "assigned_staff_id")

    op.drop_index("ix_staff_users_email", table_name="staff_users")

    op.alter_column(
        "staff_users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "staff_users",
        "username",
        existing_type=sa.String(length=100),
        nullable=False,
    )

    op.drop_column("staff_users", "phone")
    op.drop_column("staff_users", "email")
    op.drop_column("staff_users", "name")
