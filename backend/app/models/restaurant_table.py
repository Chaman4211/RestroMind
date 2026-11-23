from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(
        String(30),
        default="FREE",
        server_default=text("'FREE'"),
        nullable=False,
        index=True,
    )

    zone_coordinates: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    upload_zone_coordinates: Mapped[dict | list | None] = mapped_column(
        JSON, nullable=True
    )
    upload_camera_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("camera_sources.id", ondelete="SET NULL"), nullable=True
    )

    camera_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("camera_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    last_status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    camera_source = relationship(
        "CameraSource",
        back_populates="tables",
        foreign_keys=[camera_source_id],
    )
    occupancy_events = relationship("OccupancyEvent", back_populates="restaurant_table")
    alerts = relationship("Alert", back_populates="restaurant_table")
