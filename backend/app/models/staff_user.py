from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StaffUser(Base):
    __tablename__ = "staff_users"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )

    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    username: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )

    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(
        String(30),
        default="CLEANING_STAFF",
        server_default=text("'CLEANING_STAFF'"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assigned_alerts = relationship("Alert", back_populates="assigned_staff")
