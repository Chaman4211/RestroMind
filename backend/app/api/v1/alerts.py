from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.alert import Alert
from app.models.restaurant_table import RestaurantTable
from app.models.staff_user import StaffUser
from app.schemas.alert import AlertAssignmentUpdate, AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])

MANAGEMENT_ROLES = (
    "OWNER",
    "MANAGER",
    "ASSISTANT_MANAGER",
    "SUPERVISOR",
)

MANAGEMENT_USER = require_roles(*MANAGEMENT_ROLES)


def alert_response_query():
    return (
        select(
            Alert,
            RestaurantTable.table_number,
            RestaurantTable.name,
            StaffUser.name,
            StaffUser.role,
        )
        .join(RestaurantTable, Alert.table_id == RestaurantTable.id)
        .outerjoin(StaffUser, Alert.assigned_staff_id == StaffUser.id)
    )


def serialize_alert(result):
    alert, table_number, table_name, staff_name, staff_role = result

    return {
        "id": alert.id,
        "table_id": alert.table_id,
        "table_number": table_number,
        "table_name": table_name,
        "alert_type": alert.alert_type,
        "message": alert.message,
        "status": alert.status,
        "created_at": alert.created_at,
        "resolved_at": alert.resolved_at,
        "assigned_staff_id": alert.assigned_staff_id,
        "assigned_staff_name": staff_name,
        "assigned_staff_role": staff_role,
    }


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    status: Literal["OPEN", "RESOLVED"] | None = None,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = alert_response_query().order_by(
        Alert.created_at.desc(), Alert.id.desc()
    )

    if current_user.role == "CLEANING_STAFF":
        statement = statement.where(
            Alert.assigned_staff_id == current_user.id,
            Alert.alert_type == "CLEANING_REQUIRED",
        )
    elif current_user.role not in MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view alerts",
        )

    if status is not None:
        statement = statement.where(Alert.status == status)

    results = db.execute(statement).all()
    return [serialize_alert(result) for result in results]


@router.patch("/{alert_id}/assignment", response_model=AlertResponse)
def update_alert_assignment(
    alert_id: int,
    payload: AlertAssignmentUpdate,
    current_user: StaffUser = Depends(MANAGEMENT_USER),
    db: Session = Depends(get_db),
):
    alert = db.get(Alert, alert_id)

    if alert is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    if alert.status != "OPEN" or alert.alert_type != "CLEANING_REQUIRED":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Only open cleaning tasks can be assigned",
        )

    if payload.assigned_staff_id is not None:
        staff_member = db.get(StaffUser, payload.assigned_staff_id)

        if staff_member is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Staff member not found",
            )

        if not staff_member.is_active:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Cannot assign a task to an inactive staff member",
            )

        if staff_member.role != "CLEANING_STAFF":
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cleaning tasks can only be assigned to cleaning staff",
            )

    alert.assigned_staff_id = payload.assigned_staff_id
    db.commit()
    db.refresh(alert)

    result = db.execute(
        alert_response_query().where(Alert.id == alert_id)
    ).one()

    return serialize_alert(result)
