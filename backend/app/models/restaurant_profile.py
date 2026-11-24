from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RestaurantProfile(Base):
    __tablename__ = "restaurant_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_name: Mapped[str] = mapped_column(
        String(150), nullable=False, default="My Restaurant"
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="PKR")
