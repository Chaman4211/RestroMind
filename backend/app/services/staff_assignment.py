
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.staff_user import StaffUser


def staff_role_for_alert(alert_type: str) -> str | None:
    return {
        "CLEANING_REQUIRED": "CLEANING_STAFF",
        "UNPAID_BILL": "CASHIER",
        "SERVICE_REMINDER": "WAITER",
    }.get(alert_type)


def staff_role_for_request(request_type: str) -> str:
    return "CASHIER" if request_type == "BILL" else "WAITER"


def find_assigned_staff_id(db: Session, role: str) -> int | None:
    return db.scalar(
        select(StaffUser.id)
        .where(
            StaffUser.role == role,
            StaffUser.is_active.is_(True),
        )
        .order_by(StaffUser.id)
        .limit(1)
    )


def find_least_loaded_staff_id(connection, role: str) -> int | None:
    """Choose the active staff member with the fewest outstanding tasks."""
    from sqlalchemy import func

    metadata = StaffUser.metadata
    staff = metadata.tables["staff_users"]
    alerts = metadata.tables["alerts"]
    requests = metadata.tables["service_requests"]

    open_alerts = (
        select(func.count(alerts.c.id))
        .where(
            alerts.c.assigned_staff_id == staff.c.id,
            alerts.c.status == "OPEN",
        )
        .scalar_subquery()
    )

    open_requests = (
        select(func.count(requests.c.id))
        .where(
            requests.c.assigned_staff_id == staff.c.id,
            requests.c.status.in_(("OPEN", "ACKNOWLEDGED")),
        )
        .scalar_subquery()
    )

    statement = (
        select(staff.c.id)
        .where(
            staff.c.role == role,
            staff.c.is_active.is_(True),
        )
        .order_by(open_alerts + open_requests, staff.c.id)
        .limit(1)
    )

    return connection.scalar(statement)
