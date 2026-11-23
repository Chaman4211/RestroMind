from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, event, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.services.staff_assignment import (
    find_least_loaded_staff_id,
    staff_role_for_request,
)


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    table_id: Mapped[int] = mapped_column(
        ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurant_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    request_type: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        default="OPEN",
        server_default=text("'OPEN'"),
        nullable=False,
        index=True,
    )

    assigned_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    handled_by_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    restaurant_table = relationship("RestaurantTable")
    restaurant_order = relationship("RestaurantOrder")
    assigned_staff = relationship("StaffUser", foreign_keys=[assigned_staff_id])
    handled_by_staff = relationship("StaffUser", foreign_keys=[handled_by_staff_id])


@event.listens_for(ServiceRequest, "before_insert")
def assign_request_to_relevant_staff(mapper, connection, target):
    if target.assigned_staff_id is not None:
        return

    role = staff_role_for_request(target.request_type)
    target.assigned_staff_id = find_least_loaded_staff_id(connection, role)
