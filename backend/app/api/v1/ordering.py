import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.alert import Alert
from app.models.menu_item import MenuItem
from app.models.restaurant_order import OrderItem, RestaurantOrder
from app.models.restaurant_order_feedback import RestaurantOrderFeedback
from app.models.restaurant_table import RestaurantTable
from app.models.service_request import ServiceRequest
from app.models.staff_user import StaffUser
from app.models.table_order_session import TableOrderSession
from app.schemas.ordering import (
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
    OrderCreate,
    OrderCreatedResponse,
    OrderFeedbackCreate,
    OrderResponse,
    OrderStatusUpdate,
    SharedCartItemChange,
    SharedCartSubmit,
)
from app.services.occupancy.runtime import occupancy_service

router = APIRouter(tags=["Restaurant Ordering"])

MANAGEMENT_USER = require_roles("OWNER", "MANAGER", "ASSISTANT_MANAGER", "SUPERVISOR")

KITCHEN_USER = require_roles(
    "OWNER",
    "MANAGER",
    "ASSISTANT_MANAGER",
    "SUPERVISOR",
    "HEAD_CHEF",
    "SOUS_CHEF",
    "CHEF",
    "KITCHEN_ASSISTANT",
)


@router.get("/public/tables/{table_id}")
def get_public_table(table_id: int, db: Session = Depends(get_db)):
    """Return only the basic table details needed by a customer QR page."""
    table = db.get(RestaurantTable, table_id)

    if table is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")

    return {
        "id": table.id,
        "table_number": table.table_number,
        "name": table.name,
    }


@router.get("/menu", response_model=list[MenuItemResponse])
def get_public_menu(db: Session = Depends(get_db)):
    return (
        db.query(MenuItem)
        .filter(MenuItem.is_available.is_(True))
        .order_by(MenuItem.category, MenuItem.name)
        .all()
    )


@router.get("/menu/manage", response_model=list[MenuItemResponse])
def get_all_menu_items(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT_USER),
):
    return db.query(MenuItem).order_by(MenuItem.category, MenuItem.name).all()


@router.post(
    "/menu",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_menu_item(
    payload: MenuItemCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT_USER),
):
    data = payload.model_dump()
    data["size_prices"] = {
        key: float(value) for key, value in data.get("size_prices", {}).items()
    }
    item = MenuItem(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/menu/{item_id}", response_model=MenuItemResponse)
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT_USER),
):
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    updates = payload.model_dump(exclude_unset=True)
    if "size_prices" in updates and updates["size_prices"] is not None:
        updates["size_prices"] = {
            key: float(value) for key, value in updates["size_prices"].items()
        }
    for key, value in updates.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT_USER),
):
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    db.delete(item)
    db.commit()


def _get_or_create_table_session(db: Session, table_id: int) -> TableOrderSession:
    table = db.get(RestaurantTable, table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")

    session = (
        db.query(TableOrderSession)
        .filter(TableOrderSession.table_id == table_id)
        .with_for_update()
        .first()
    )
    if session is None:
        session = TableOrderSession(table_id=table_id, cart=[], round_number=1)
        db.add(session)
        try:
            db.commit()
        except Exception:
            db.rollback()
            session = (
                db.query(TableOrderSession)
                .filter(TableOrderSession.table_id == table_id)
                .with_for_update()
                .first()
            )
            if session is None:
                raise
        else:
            db.refresh(session)
    return session


@router.get("/public/tables/{table_id}/shared-cart")
def get_shared_table_cart(table_id: int, db: Session = Depends(get_db)):
    session = _get_or_create_table_session(db, table_id)
    return {
        "table_id": session.table_id,
        "round_number": session.round_number,
        "last_order_token": session.last_order_token,
        "last_order_round": session.last_order_round,
        "cart": session.cart or [],
    }


@router.post("/public/tables/{table_id}/shared-cart/items")
def change_shared_cart_item(
    table_id: int,
    payload: SharedCartItemChange,
    db: Session = Depends(get_db),
):
    session = _get_or_create_table_session(db, table_id)
    session = (
        db.query(TableOrderSession)
        .filter(TableOrderSession.id == session.id)
        .with_for_update()
        .first()
    )

    menu_item = db.get(MenuItem, payload.menu_item_id)
    if menu_item is None or not menu_item.is_available:
        raise HTTPException(status_code=400, detail="This menu item is unavailable")

    size_prices = menu_item.size_prices or {}
    if size_prices:
        if payload.size is None or payload.size not in size_prices:
            raise HTTPException(
                status_code=400, detail="Please select a valid item size"
            )
        unit_price = Decimal(str(size_prices[payload.size]))
    else:
        if payload.size is not None:
            raise HTTPException(status_code=400, detail="This item has no size options")
        unit_price = menu_item.price

    cart = list(session.cart or [])
    key = (payload.menu_item_id, payload.size or "", payload.notes or "")
    found = False

    for line in cart:
        line_key = (
            int(line["menu_item_id"]),
            line.get("size") or "",
            line.get("notes") or "",
        )
        if line_key == key:
            quantity = int(line["quantity"]) + payload.quantity_delta
            if quantity <= 0:
                cart.remove(line)
            elif quantity > 30:
                raise HTTPException(
                    status_code=400, detail="Maximum quantity is 30 per cart line"
                )
            else:
                line["quantity"] = quantity
            found = True
            break

    if not found and payload.quantity_delta > 0:
        cart.append(
            {
                "menu_item_id": menu_item.id,
                "item_name": menu_item.name,
                "size": payload.size,
                "unit_price": str(unit_price),
                "quantity": payload.quantity_delta,
                "notes": payload.notes,
            }
        )

    session.cart = cart
    db.commit()
    db.refresh(session)
    return {
        "table_id": session.table_id,
        "round_number": session.round_number,
        "last_order_token": session.last_order_token,
        "last_order_round": session.last_order_round,
        "cart": session.cart or [],
    }


@router.post(
    "/public/tables/{table_id}/shared-cart/submit",
    response_model=OrderCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_shared_table_cart(
    table_id: int,
    payload: SharedCartSubmit,
    db: Session = Depends(get_db),
):
    session = (
        db.query(TableOrderSession)
        .filter(TableOrderSession.table_id == table_id)
        .with_for_update()
        .first()
    )
    if session is None:
        raise HTTPException(
            status_code=404, detail="No shared cart exists for this table"
        )

    cart = list(session.cart or [])
    if not cart:
        raise HTTPException(status_code=409, detail="The shared cart is empty")

    table = db.get(RestaurantTable, table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")

    order_items = []
    total = Decimal("0.00")

    for line in cart:
        menu_item = db.get(MenuItem, int(line["menu_item_id"]))
        if menu_item is None or not menu_item.is_available:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{line.get('item_name', 'A selected item')} is no longer available"
                ),
            )

        quantity = int(line["quantity"])
        size = line.get("size")
        size_prices = menu_item.size_prices or {}

        if size_prices:
            if not size or size not in size_prices:
                raise HTTPException(
                    status_code=409,
                    detail=f"Please reselect the size for {menu_item.name}",
                )
            unit_price = Decimal(str(size_prices[size]))
        else:
            if size:
                raise HTTPException(
                    status_code=409, detail=f"{menu_item.name} no longer has that size"
                )
            unit_price = menu_item.price

        total += unit_price * quantity
        order_items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                item_name=menu_item.name,
                size=size,
                unit_price=unit_price,
                quantity=quantity,
                notes=line.get("notes"),
            )
        )

    order = RestaurantOrder(
        order_number=f"RM-{datetime.now(UTC):%y%m%d}-{uuid4().hex[:6].upper()}",
        public_token=secrets.token_urlsafe(32),
        table_id=table.id,
        customer_name=payload.customer_name,
        notes=payload.notes,
        customer_allergies=payload.customer_allergies,
        allergy_notes=payload.allergy_notes,
        status="NEW",
        total_amount=total,
        items=order_items,
    )

    db.add(order)
    occupancy_service.mark_occupied(db, table.id)
    session.last_order_token = order.public_token
    session.last_order_round = session.round_number
    session.cart = []
    session.round_number += 1
    db.commit()
    db.refresh(order)
    return order


@router.post(
    "/orders",
    response_model=OrderCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    table = db.get(RestaurantTable, payload.table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")

    order_items = []
    total = Decimal("0.00")

    for requested in payload.items:
        menu_item = db.get(MenuItem, requested.menu_item_id)

        if menu_item is None or not menu_item.is_available:
            raise HTTPException(
                status_code=400,
                detail=f"Menu item {requested.menu_item_id} is unavailable",
            )

        size_prices = menu_item.size_prices or {}
        if size_prices:
            if requested.size is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Please select a size for {menu_item.name}",
                )
            if requested.size not in size_prices:
                raise HTTPException(
                    status_code=400,
                    detail=f"Selected size is not available for {menu_item.name}",
                )
            unit_price = Decimal(str(size_prices[requested.size]))
        else:
            if requested.size is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"{menu_item.name} does not have size options",
                )
            unit_price = menu_item.price

        total += unit_price * requested.quantity

        order_items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                item_name=menu_item.name,
                size=requested.size,
                unit_price=unit_price,
                quantity=requested.quantity,
                notes=requested.notes,
            )
        )

    order = RestaurantOrder(
        order_number=f"RM-{datetime.now(UTC):%y%m%d}-{uuid4().hex[:6].upper()}",
        public_token=secrets.token_urlsafe(32),
        table_id=table.id,
        customer_name=payload.customer_name,
        notes=payload.notes,
        customer_allergies=payload.customer_allergies,
        allergy_notes=payload.allergy_notes,
        status="NEW",
        total_amount=total,
        items=order_items,
    )

    db.add(order)
    occupancy_service.mark_occupied(db, table.id)
    db.commit()
    db.refresh(order)

    return order


@router.get("/orders/track/{public_token}", response_model=OrderResponse)
def track_order(public_token: str, db: Session = Depends(get_db)):
    order = (
        db.query(RestaurantOrder)
        .options(joinedload(RestaurantOrder.items))
        .filter(RestaurantOrder.public_token == public_token)
        .first()
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@router.post("/orders/track/{public_token}/feedback")
def submit_order_feedback(
    public_token: str,
    payload: OrderFeedbackCreate,
    db: Session = Depends(get_db),
):
    order = (
        db.query(RestaurantOrder)
        .filter(RestaurantOrder.public_token == public_token)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_status != "PAID":
        raise HTTPException(
            status_code=409, detail="Feedback is available after payment is confirmed."
        )
    entry = (
        db.query(RestaurantOrderFeedback)
        .filter(RestaurantOrderFeedback.order_id == order.id)
        .first()
    )
    if entry is None:
        entry = RestaurantOrderFeedback(
            order_id=order.id, rating=payload.rating, feedback=payload.feedback
        )
        db.add(entry)
    else:
        entry.rating = payload.rating
        entry.feedback = payload.feedback
    db.commit()
    db.refresh(entry)
    return {
        "id": entry.id,
        "rating": entry.rating,
        "feedback": entry.feedback,
        "created_at": entry.created_at,
    }


@router.post(
    "/orders/track/{public_token}/eating-complete",
    response_model=OrderResponse,
)
def mark_eating_complete(public_token: str, db: Session = Depends(get_db)):
    """Allow a customer to mark their served order as finished eating."""
    order = (
        db.query(RestaurantOrder)
        .options(joinedload(RestaurantOrder.items))
        .filter(RestaurantOrder.public_token == public_token)
        .first()
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "SERVED":
        raise HTTPException(
            status_code=409,
            detail="You can mark eating complete after your order is served.",
        )

    # Idempotent: repeated requests do not change the original completion time.
    if order.eating_completed_at is None:
        order.eating_completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(order)

    return order


class OrderPaymentSelection(BaseModel):
    method: Literal[
        "Cash", "Card", "JazzCash", "Easypaisa", "SadaPay", "NayaPay", "Other bank app"
    ]
    provider: str | None = Field(default=None, max_length=60)


PAYMENT_STAFF = require_roles(
    "OWNER", "MANAGER", "ASSISTANT_MANAGER", "SUPERVISOR", "CASHIER"
)


@router.post(
    "/orders/track/{public_token}/payment",
    response_model=OrderResponse,
)
def select_order_payment(
    public_token: str,
    payload: OrderPaymentSelection,
    db: Session = Depends(get_db),
):
    """Save a guest's payment choice and notify staff; this does not mark it paid."""
    order = (
        db.query(RestaurantOrder)
        .options(joinedload(RestaurantOrder.items))
        .filter(RestaurantOrder.public_token == public_token)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "SERVED" or order.eating_completed_at is None:
        raise HTTPException(
            status_code=409, detail="Checkout is available after eating is complete."
        )
    if order.payment_status == "PAID":
        raise HTTPException(status_code=409, detail="This order has already been paid.")

    if payload.method in {
        "JazzCash",
        "Easypaisa",
        "SadaPay",
        "NayaPay",
        "Other bank app",
    }:
        provider = payload.method
    else:
        provider = payload.provider

    order.payment_method = payload.method
    order.payment_provider = provider
    order.payment_status = "PENDING"
    order.payment_requested_at = datetime.now(UTC)

    existing = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.order_id == order.id,
            ServiceRequest.request_type == "BILL",
            ServiceRequest.status != "COMPLETED",
        )
        .first()
    )

    if existing is None:
        db.add(
            ServiceRequest(
                table_id=order.table_id,
                order_id=order.id,
                request_type="BILL",
                message=(
                    f"Order {order.order_number}: customer selected {payload.method}"
                    f"{f' ({provider})' if provider else ''}. "
                    f"Amount: Rs. {order.total_amount}. "
                    "Payment is awaiting staff confirmation."
                ),
            )
        )
    else:
        existing.message = (
            f"Order {order.order_number}: customer selected {payload.method}"
            f"{f' ({provider})' if provider else ''}. "
            f"Amount: Rs. {order.total_amount}. Payment is awaiting staff confirmation."
        )
        existing.status = "OPEN"
        existing.acknowledged_at = None
        existing.completed_at = None
        existing.handled_by_staff_id = None

    db.commit()
    db.refresh(order)
    return order


@router.post(
    "/orders/{order_id}/confirm-payment",
    response_model=OrderResponse,
)
def confirm_order_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(PAYMENT_STAFF),
):
    """Only authorized staff can confirm that money was actually received."""
    order = (
        db.query(RestaurantOrder)
        .options(joinedload(RestaurantOrder.items))
        .filter(RestaurantOrder.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_status == "PAID":
        return order
    if order.payment_status != "PENDING":
        raise HTTPException(
            status_code=409, detail="There is no pending payment to confirm."
        )

    now = datetime.now(UTC)
    order.payment_status = "PAID"
    order.payment_confirmed_at = now

    bill_request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.order_id == order.id,
            ServiceRequest.request_type == "BILL",
        )
        .first()
    )
    if bill_request is not None:
        bill_request.status = "COMPLETED"
        bill_request.completed_at = now
        bill_request.handled_by_staff_id = current_user.id

    db.flush()

    table = db.get(RestaurantTable, order.table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")

    visit_started_at = table.last_status_changed_at or table.created_at

    unpaid_alert = db.scalar(
        select(Alert).where(
            Alert.table_id == order.table_id,
            Alert.alert_type == "UNPAID_BILL",
            Alert.status == "OPEN",
        )
    )

    if unpaid_alert is not None:
        another_unpaid_order = db.scalar(
            select(RestaurantOrder.id)
            .where(
                RestaurantOrder.table_id == order.table_id,
                RestaurantOrder.status != "CANCELLED",
                RestaurantOrder.payment_status != "PAID",
                RestaurantOrder.created_at >= visit_started_at,
            )
            .limit(1)
        )

        if another_unpaid_order is None:
            unpaid_alert.status = "RESOLVED"
            unpaid_alert.resolved_at = now
            occupancy_service.mark_needs_cleaning(
                db,
                order.table_id,
                description=(
                    "Payment received after customer departure. "
                    "Table requires cleaning."
                ),
                timestamp=now,
            )

    db.commit()
    db.refresh(order)
    return order


@router.get("/orders/kitchen", response_model=list[OrderResponse])
def get_kitchen_orders(
    include_history: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(KITCHEN_USER),
):
    orders_query = db.query(RestaurantOrder).options(joinedload(RestaurantOrder.items))

    if include_history:
        orders_query = orders_query.filter(
            RestaurantOrder.status.in_(["SERVED", "CANCELLED"])
        ).order_by(RestaurantOrder.created_at.desc())
    else:
        orders_query = orders_query.filter(
            RestaurantOrder.status.in_(["NEW", "PREPARING", "READY"])
        ).order_by(RestaurantOrder.created_at.asc())

    return orders_query.all()


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(KITCHEN_USER),
):
    order = (
        db.query(RestaurantOrder)
        .options(joinedload(RestaurantOrder.items))
        .filter(RestaurantOrder.id == order_id)
        .first()
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed_transitions = {
        "NEW": {"PREPARING", "CANCELLED"},
        "PREPARING": {"READY", "CANCELLED"},
        "READY": {"SERVED", "CANCELLED"},
        "SERVED": set(),
        "CANCELLED": set(),
    }

    if payload.status not in allowed_transitions.get(order.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change order from {order.status} to {payload.status}",
        )

    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order
