from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    size_prices: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'::json"), nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ingredients: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    allergens: Mapped[list] = mapped_column(JSON,
        default=list, server_default=text("'[]'"), nullable=False
    )
    spice_level: Mapped[str] = mapped_column(
        String(20), default="MILD", server_default=text("'MILD'"), nullable=False
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
