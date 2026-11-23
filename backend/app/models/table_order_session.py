from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TableOrderSession(Base):
    __tablename__ = "table_order_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    cart: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    round_number: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    last_order_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_order_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )

    table = relationship("RestaurantTable")
