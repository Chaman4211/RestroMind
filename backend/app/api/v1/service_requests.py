from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.restaurant_order import RestaurantOrder
from app.models.restaurant_table import RestaurantTable
from app.models.service_request import ServiceRequest
from app.models.staff_user import StaffUser
from app.schemas.service_request import (
    ServiceRequestCreate,
    ServiceRequestResponse,
    ServiceRequestStatusUpdate,
)

router = APIRouter(prefix="/service-requests", tags=["Service Requests"])

MANAGEMENT_ROLES = ("OWNER", "MANAGER", "ASSISTANT_MANAGER", "SUPERVISOR")

SERVICE_STAFF = require_roles(
    *MANAGEMENT_ROLES,
    "WAITER",
    "HOST",
    "CASHIER",
    "BARTENDER",
    "BARISTA",
)


def serialize_request(item: ServiceRequest) -> dict:
    return {
        "id": item.id,
        "table_id": item.table_id,
        "order_id": item.order_id,
        "table_number": item.restaurant_table.table_number,
        "table_name": item.restaurant_table.name,
        "request_type": item.request_type,
        "message": item.message,
        "status": item.status,
        "created_at": item.created_at,
        "acknowledged_at": item.acknowledged_at,
        "completed_at": item.completed_at,
        "assigned_staff_id": item.assigned_staff_id,
        "assigned_staff_name": (
            item.assigned_staff.name if item.assigned_staff else None
        ),
        "handled_by_staff_id": item.handled_by_staff_id,
        "handled_by_staff_name": (
            item.handled_by_staff.name if item.handled_by_staff else None
        ),
    }


def request_options():
    return (
        joinedload(ServiceRequest.restaurant_table),
        joinedload(ServiceRequest.assigned_staff),
        joinedload(ServiceRequest.handled_by_staff),
    )


@router.post(
    "",
    response_model=ServiceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service_request(
    payload: ServiceRequestCreate,
    db: Session = Depends(get_db),
):
    """Public endpoint used by guests opening their table QR code."""
    table = db.get(RestaurantTable, payload.table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")

    order = None
    if payload.order_token:
        order = (
            db.query(RestaurantOrder)
            .filter(RestaurantOrder.public_token == payload.order_token)
            .first()
        )
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.table_id != table.id:
            raise HTTPException(
                status_code=403,
                detail="This order does not belong to the selected table",
            )

    item = ServiceRequest(
        table_id=table.id,
        order_id=order.id if order else None,
        request_type=payload.request_type,
        message=payload.message.strip() if payload.message else None,
    )
    db.add(item)
    db.commit()

    item = (
        db.query(ServiceRequest)
        .options(*request_options())
        .filter(ServiceRequest.id == item.id)
        .one()
    )
    return serialize_request(item)


@router.get("", response_model=list[ServiceRequestResponse])
def get_service_requests(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(SERVICE_STAFF),
):
    query = db.query(ServiceRequest).options(*request_options())

    if current_user.role not in MANAGEMENT_ROLES:
        query = query.filter(ServiceRequest.assigned_staff_id == current_user.id)

    items = query.order_by(ServiceRequest.created_at.desc()).limit(200).all()
    return [serialize_request(item) for item in items]


@router.get(
    "/table/{table_id}",
    response_model=list[ServiceRequestResponse],
)
def get_table_service_requests(
    table_id: int,
    db: Session = Depends(get_db),
):
    """Public status lookup for guests using their table QR code."""
    table = db.get(RestaurantTable, table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")

    items = (
        db.query(ServiceRequest)
        .options(*request_options())
        .filter(ServiceRequest.table_id == table_id)
        .order_by(ServiceRequest.created_at.desc())
        .limit(30)
        .all()
    )
    return [serialize_request(item) for item in items]


@router.get(
    "/order/{public_token}",
    response_model=list[ServiceRequestResponse],
)
def get_order_service_requests(
    public_token: str,
    db: Session = Depends(get_db),
):
    """Public status lookup limited to the order opened by this customer."""
    order = (
        db.query(RestaurantOrder)
        .filter(RestaurantOrder.public_token == public_token)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    items = (
        db.query(ServiceRequest)
        .options(*request_options())
        .filter(ServiceRequest.order_id == order.id)
        .order_by(ServiceRequest.created_at.desc())
        .limit(30)
        .all()
    )
    return [serialize_request(item) for item in items]


@router.patch(
    "/{request_id}/status",
    response_model=ServiceRequestResponse,
)
def update_service_request_status(
    request_id: int,
    payload: ServiceRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(SERVICE_STAFF),
):
    item = (
        db.query(ServiceRequest)
        .options(*request_options())
        .filter(ServiceRequest.id == request_id)
        .first()
    )

    if item is None:
        raise HTTPException(status_code=404, detail="Service request not found")

    if (
        current_user.role not in MANAGEMENT_ROLES
        and item.assigned_staff_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="This request is assigned to another staff member",
        )

    now = datetime.now(UTC)

    if payload.status == "ACKNOWLEDGED":
        if item.status == "COMPLETED":
            raise HTTPException(
                status_code=409, detail="This request is already completed"
            )
        if item.status == "OPEN":
            item.status = "ACKNOWLEDGED"
            item.acknowledged_at = now
            item.handled_by_staff_id = current_user.id

    elif payload.status == "COMPLETED":
        if item.request_type == "BILL" and item.order_id is not None:
            raise HTTPException(
                status_code=409,
                detail="Use Confirm Payment to complete an order bill.",
            )
        if item.status == "OPEN":
            raise HTTPException(
                status_code=409,
                detail="A request must be acknowledged before completion",
            )
        if item.status != "COMPLETED":
            item.status = "COMPLETED"
            item.completed_at = now
            item.handled_by_staff_id = current_user.id

    db.commit()
    item = (
        db.query(ServiceRequest)
        .options(*request_options())
        .filter(ServiceRequest.id == request_id)
        .one()
    )
    return serialize_request(item)
