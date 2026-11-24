from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RestaurantOrder(Base):
    __tablename__ = "restaurant_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    public_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("restaurant_tables.id", ondelete="RESTRICT"), nullable=False
    )
    customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_allergies: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    allergy_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="NEW", server_default=text("'NEW'"), nullable=False
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    eating_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payment_provider: Mapped[str | None] = mapped_column(String(60), nullable=True)
    transaction_reference: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), default="UNPAID", server_default=text("'UNPAID'"), nullable=False
    )
    payment_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    table = relationship("RestaurantTable")
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("restaurant_orders.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True
    )
    item_name: Mapped[str] = mapped_column(String(150), nullable=False)
    size: Mapped[str | None] = mapped_column(String(30), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)

    order = relationship("RestaurantOrder", back_populates="items")
