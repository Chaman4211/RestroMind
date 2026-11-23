from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    event,
    func,
    inspect,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.services.staff_assignment import (
    find_least_loaded_staff_id,
    staff_role_for_alert,
)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)

    table_id: Mapped[int] = mapped_column(
        ForeignKey("restaurant_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assigned_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(30),
        default="OPEN",
        server_default=text("'OPEN'"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    restaurant_table = relationship("RestaurantTable", back_populates="alerts")
    assigned_staff = relationship("StaffUser", back_populates="assigned_alerts")


@event.listens_for(Alert, "before_insert")
def assign_alert_to_relevant_staff(mapper, connection, target):
    if target.assigned_staff_id is not None:
        return

    # Respect an explicitly supplied None (for example, an intentionally
    # unassigned task). Auto-assign only when the field was left unset.
    if inspect(target).attrs.assigned_staff_id.history.has_changes():
        return

    role = staff_role_for_alert(target.alert_type)
    if role is None:
        return

    target.assigned_staff_id = find_least_loaded_staff_id(connection, role)
