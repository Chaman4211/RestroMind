import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.security import (
    create_notification_token,
    decode_access_token,
)
from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.restaurant_table import RestaurantTable
from app.models.staff_user import StaffUser

router = APIRouter(prefix="/alerts", tags=["Notifications"])

MANAGEMENT_ROLES = ("OWNER", "MANAGER", "ASSISTANT_MANAGER", "SUPERVISOR")


@router.post("/notification-token")
def issue_notification_token(
    current_user: StaffUser = Depends(get_current_user),
):
    return {"token": create_notification_token(str(current_user.id))}


@router.websocket("/notifications")
async def staff_notifications(websocket: WebSocket, token: str):
    try:
        payload = decode_access_token(token)
        if payload.get("purpose") != "staff_notifications":
            raise ValueError("Invalid notification token purpose")  # noqa: TRY301
        staff_id = int(payload["sub"])
        expires_at = float(payload["exp"])
    except (ValueError, TypeError, KeyError, Exception):
        await websocket.close(code=1008, reason="Invalid notification token")
        return

    with SessionLocal() as db:
        staff = db.get(StaffUser, staff_id)
        if staff is None or not staff.is_active:
            await websocket.close(code=1008, reason="Staff account unavailable")
            return

        role = staff.role

        initial_query = select(Alert.id).where(Alert.status == "OPEN")
        if role not in MANAGEMENT_ROLES:
            initial_query = initial_query.where(Alert.assigned_staff_id == staff_id)
        seen_ids = set(db.scalars(initial_query).all())

    await websocket.accept()

    try:
        await websocket.send_json({"type": "connected"})

        while True:
            if datetime.now(UTC).timestamp() >= expires_at:
                await websocket.close(
                    code=1008,
                    reason="Notification token expired",
                )
                return

            with SessionLocal() as db:
                staff = db.get(StaffUser, staff_id)
                if staff is None or not staff.is_active:
                    await websocket.close(
                        code=1008,
                        reason="Staff account unavailable",
                    )
                    return

                query = (
                    select(
                        Alert.id,
                        Alert.alert_type,
                        Alert.message,
                        RestaurantTable.table_number,
                        Alert.created_at,
                    )
                    .join(
                        RestaurantTable,
                        Alert.table_id == RestaurantTable.id,
                    )
                    .where(Alert.status == "OPEN")
                    .order_by(Alert.id.asc())
                )

                if role not in MANAGEMENT_ROLES:
                    query = query.where(Alert.assigned_staff_id == staff_id)

                rows = db.execute(query).all()

            for alert_id, alert_type, message, table_number, created_at in rows:
                if alert_id in seen_ids:
                    continue

                seen_ids.add(alert_id)
                await websocket.send_json(
                    {
                        "type": "alert",
                        "id": alert_id,
                        "alert_type": alert_type,
                        "message": message,
                        "table_number": table_number,
                        "created_at": created_at.isoformat() if created_at else None,
                    }
                )

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        pass
