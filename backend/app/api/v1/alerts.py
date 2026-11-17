from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.alert import Alert
from app.models.restaurant_table import RestaurantTable
from app.schemas.alert import AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    status: Literal["OPEN", "RESOLVED"] | None = None,
    db: Session = Depends(get_db),
):
    statement = (
        select(Alert, RestaurantTable.table_number, RestaurantTable.name)
        .join(RestaurantTable, Alert.table_id == RestaurantTable.id)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
    )

    if status is not None:
        statement = statement.where(Alert.status == status)

    results = db.execute(statement).all()

    return [
        {
            "id": alert.id,
            "table_id": alert.table_id,
            "table_number": table_number,
            "table_name": table_name,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "status": alert.status,
            "created_at": alert.created_at,
            "resolved_at": alert.resolved_at,
        }
        for alert, table_number, table_name in results
    ]
