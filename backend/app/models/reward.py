from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RewardAccount(Base):
    __tablename__ = "reward_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RewardClaim(Base):
    __tablename__ = "reward_claims"
    __table_args__ = (
        UniqueConstraint(
            "table_id", "challenge_date", name="uq_reward_table_daily_challenge"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    challenge_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    points_awarded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VisitorRewardAccount(Base):
    __tablename__ = "visitor_reward_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VisitorRewardClaim(Base):
    __tablename__ = "visitor_reward_claims"
    __table_args__ = (
        UniqueConstraint(
            "visitor_id",
            "challenge_date",
            name="uq_visitor_reward_daily_challenge",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    visitor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    challenge_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    points_awarded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
