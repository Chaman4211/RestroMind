from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.alert import Alert
from app.models.camera_source import CameraSource
from app.models.occupancy_event import OccupancyEvent
from app.models.restaurant_table import RestaurantTable
from app.models.staff_user import StaffUser
from app.schemas.restaurant_table import (
    CleaningReportRequest,
    RestaurantTableCreate,
    RestaurantTableResponse,
    RestaurantTableUpdate,
)
from app.services.occupancy.runtime import occupancy_service

router = APIRouter(prefix="/restaurant-tables", tags=["Restaurant Tables"])

MANAGEMENT_ROLES = (
    "OWNER",
    "MANAGER",
    "ASSISTANT_MANAGER",
    "SUPERVISOR",
)

TABLE_MANAGEMENT_ROLES = (
    "OWNER",
    "MANAGER",
    "ASSISTANT_MANAGER",
)

MANAGEMENT_USER = require_roles(*MANAGEMENT_ROLES)
TABLE_MANAGEMENT_USER = require_roles(*TABLE_MANAGEMENT_ROLES)


def validate_camera_source(db: Session, camera_source_id: int | None):
    if camera_source_id is None:
        return

    camera_source = db.get(CameraSource, camera_source_id)

    if camera_source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera source not found",
        )

    if not camera_source.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot assign an inactive camera source",
        )


def validate_upload_camera_source(db: Session, camera_source_id: int | None):
    if camera_source_id is None:
        return

    camera_source = db.get(CameraSource, camera_source_id)
    if camera_source is None:
        raise HTTPException(status_code=404, detail="Upload camera source not found")
    if not camera_source.is_active or camera_source.source_type != "UPLOAD":
        raise HTTPException(
            status_code=409,
            detail="Select an active upload video source",
        )


@router.post(
    "",
    response_model=RestaurantTableResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant_table(
    payload: RestaurantTableCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(TABLE_MANAGEMENT_USER),
):
    validate_camera_source(db, payload.camera_source_id)
    validate_upload_camera_source(db, payload.upload_camera_source_id)

    existing_table = db.scalar(
        select(RestaurantTable).where(
            RestaurantTable.table_number == payload.table_number
        )
    )

    if existing_table:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Table number already exists",
        )

    restaurant_table = RestaurantTable(**payload.model_dump())

    try:
        db.add(restaurant_table)
        db.commit()
        db.refresh(restaurant_table)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Table number already exists or camera assignment is invalid",
        ) from None

    return restaurant_table


@router.get("", response_model=list[RestaurantTableResponse])
def list_restaurant_tables(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT_USER),
):
    statement = select(RestaurantTable).order_by(RestaurantTable.id)
    return db.scalars(statement).all()


@router.get("/history")
def get_restaurant_table_history(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT_USER),
):
    statement = (
        select(
            OccupancyEvent,
            RestaurantTable.table_number,
            RestaurantTable.name,
        )
        .join(RestaurantTable, OccupancyEvent.table_id == RestaurantTable.id)
        .order_by(OccupancyEvent.created_at.asc(), OccupancyEvent.id.asc())
    )
    rows = db.execute(statement).all()

    events = []
    active_visits = {}
    visits = []

    for event, table_number, table_name in rows:
        events.append({
            "id": event.id,
            "table_id": event.table_id,
            "table_number": table_number,
            "table_name": table_name,
            "previous_status": event.previous_status,
            "new_status": event.new_status,
            "description": event.description,
            "created_at": event.created_at,
        })

        if event.new_status == "OCCUPIED":
            active_visits[event.table_id] = {
                "table_id": event.table_id,
                "table_number": table_number,
                "table_name": table_name,
                "started_at": event.created_at,
            }
        elif (
            event.new_status in ("FREE", "NEEDS_CLEANING")
            and event.table_id in active_visits
        ):
            visit = active_visits.pop(event.table_id)
            ended_at = event.created_at
            visit["ended_at"] = ended_at
            visit["duration_seconds"] = max(
                0, int((ended_at - visit["started_at"]).total_seconds())
            )
            visit["is_ongoing"] = False
            visits.append(visit)

    for visit in active_visits.values():
        started_at = visit["started_at"]
        ended_at = datetime.now(started_at.tzinfo)
        visit["ended_at"] = None
        visit["duration_seconds"] = max(
            0, int((ended_at - started_at).total_seconds())
        )
        visit["is_ongoing"] = True
        visits.append(visit)

    events.sort(
        key=lambda item: (item["created_at"], item["id"]),
        reverse=True,
    )
    visits.sort(key=lambda item: item["started_at"], reverse=True)

    return {
        "events": events[:20],
        "visits": visits[:20],
    }


@router.get("/{table_id}", response_model=RestaurantTableResponse)
def get_restaurant_table(
    table_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT_USER),
):
    restaurant_table = db.get(RestaurantTable, table_id)

    if restaurant_table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant table not found",
        )

    return restaurant_table


@router.patch("/{table_id}", response_model=RestaurantTableResponse)
def update_restaurant_table(
    table_id: int,
    payload: RestaurantTableUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT_USER),
):
    restaurant_table = db.get(RestaurantTable, table_id)

    if restaurant_table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant table not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "camera_source_id" in update_data:
        validate_camera_source(db, update_data["camera_source_id"])
    if "upload_camera_source_id" in update_data:
        validate_upload_camera_source(db, update_data["upload_camera_source_id"])

    for field, value in update_data.items():
        setattr(restaurant_table, field, value)

    try:
        db.commit()
        db.refresh(restaurant_table)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid camera assignment",
        ) from None

    return restaurant_table


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_restaurant_table(
    table_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(TABLE_MANAGEMENT_USER),
):
    restaurant_table = db.get(RestaurantTable, table_id)

    if restaurant_table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant table not found",
        )

    has_events = db.scalar(
        select(OccupancyEvent.id)
        .where(OccupancyEvent.table_id == table_id)
        .limit(1)
    )

    has_alerts = db.scalar(
        select(Alert.id)
        .where(Alert.table_id == table_id)
        .limit(1)
    )

    if has_events or has_alerts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a table with occupancy history or alerts",
        )

    db.delete(restaurant_table)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{table_id}/report-cleaning")
def report_table_cleaning_required(
    table_id: int,
    payload: CleaningReportRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    if current_user.role not in (*MANAGEMENT_ROLES, "WAITER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to report cleaning needs",
        )

    try:
        return occupancy_service.report_cleaning_required(
            db=db,
            table_id=table_id,
            reported_by=current_user.name,
            reason=payload.reason,
        )
    except ValueError as error:
        if str(error) == "Restaurant table not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from None
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from None


@router.post(
    "/{table_id}/customer-left",
    response_model=RestaurantTableResponse,
)
def mark_table_customer_left(
    table_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    if current_user.role not in (*MANAGEMENT_ROLES, "WAITER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to mark a customer as left",
        )

    try:
        occupancy_service.mark_customer_left(db, table_id)
        db.commit()
        return db.get(RestaurantTable, table_id)
    except ValueError as error:
        db.rollback()
        if str(error) == "Restaurant table not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from None
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from None


@router.post(
    "/{table_id}/confirm-cleaning",
    response_model=RestaurantTableResponse,
)
def confirm_table_cleaning(
    table_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    if current_user.role not in (*MANAGEMENT_ROLES, "CLEANING_STAFF"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to confirm table cleaning",
        )

    if current_user.role == "CLEANING_STAFF":
        open_alerts = db.scalars(
            select(Alert).where(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
        ).all()

        if not open_alerts or any(
            alert.assigned_staff_id != current_user.id
            for alert in open_alerts
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only confirm cleaning tasks assigned to you",
            )

    try:
        occupancy_service.confirm_cleaning(db, table_id)
    except ValueError as error:
        if str(error) == "Restaurant table not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from None
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from None

    return db.get(RestaurantTable, table_id)
