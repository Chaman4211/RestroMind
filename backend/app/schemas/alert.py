from datetime import datetime

from pydantic import BaseModel


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
