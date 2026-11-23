from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ServiceRequestType = Literal[
    "CALL_WAITER",
    "WATER",
    "TISSUES",
    "CUTLERY",
    "BILL",
    "WIFI",
    "OTHER",
]


class ServiceRequestCreate(BaseModel):
    table_id: int = Field(gt=0)
    order_token: str | None = Field(default=None, min_length=1, max_length=128)
    request_type: ServiceRequestType
    message: str | None = Field(default=None, max_length=250)


class ServiceRequestStatusUpdate(BaseModel):
    status: Literal["ACKNOWLEDGED", "COMPLETED"]


class ServiceRequestResponse(BaseModel):
    id: int
    table_id: int
    order_id: int | None = None
    table_number: str
    table_name: str
    request_type: str
    message: str | None
    status: str
    created_at: datetime
    acknowledged_at: datetime | None
    completed_at: datetime | None
    assigned_staff_id: int | None
    assigned_staff_name: str | None
    handled_by_staff_id: int | None
    handled_by_staff_name: str | None
