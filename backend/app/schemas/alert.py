from datetime import datetime

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: int
    table_id: int
    table_number: str
    table_name: str
    alert_type: str
    message: str
    status: str
    created_at: datetime
    resolved_at: datetime | None
    assigned_staff_id: int | None = None
    assigned_staff_name: str | None = None
    assigned_staff_role: str | None = None


class AlertAssignmentUpdate(BaseModel):
    assigned_staff_id: int | None = Field(default=None, gt=0)
