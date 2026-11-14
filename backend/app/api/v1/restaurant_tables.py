from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.alert import Alert
from app.models.camera_source import CameraSource
from app.models.occupancy_event import OccupancyEvent
from app.models.restaurant_table import RestaurantTable
from app.schemas.restaurant_table import (
    RestaurantTableCreate,
    RestaurantTableResponse,
    RestaurantTableUpdate,
)
from app.services.occupancy.runtime import occupancy_service

router = APIRouter(prefix="/restaurant-tables", tags=["Restaurant Tables"])



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


@router.post(
    "",
    response_model=RestaurantTableResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant_table(
    payload: RestaurantTableCreate,
    db: Session = Depends(get_db),
):
    validate_camera_source(db, payload.camera_source_id)

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
def list_restaurant_tables(db: Session = Depends(get_db)):
    statement = select(RestaurantTable).order_by(RestaurantTable.id)
    return db.scalars(statement).all()


@router.get("/{table_id}", response_model=RestaurantTableResponse)
def get_restaurant_table(
    table_id: int,
    db: Session = Depends(get_db),
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


@router.post("/{table_id}/confirm-cleaning", response_model=RestaurantTableResponse)
def confirm_table_cleaning(
    table_id: int,
    db: Session = Depends(get_db),
):
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
