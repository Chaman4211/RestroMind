from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GameRoom(Base):
    __tablename__ = "game_rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_code: Mapped[str] = mapped_column(
        String(8), unique=True, nullable=False, index=True
    )
    game_type: Mapped[str] = mapped_column(String(30), nullable=False)
    board: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="WAITING"
    )
    current_turn: Mapped[str | None] = mapped_column(String(1), nullable=True)
    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)
    player_x_id: Mapped[str] = mapped_column(String(36), nullable=False)
    player_o_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    player_x_table_id: Mapped[int] = mapped_column(nullable=False)
    player_o_table_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
