from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StaffRole = Literal[
    "OWNER",
    "MANAGER",
    "ASSISTANT_MANAGER",
    "SUPERVISOR",
    "HEAD_CHEF",
    "SOUS_CHEF",
    "CHEF",
    "KITCHEN_ASSISTANT",
    "DISHWASHER",
    "WAITER",
    "HOST",
    "CASHIER",
    "BARTENDER",
    "BARISTA",
    "CLEANING_STAFF",
    "INVENTORY_MANAGER",
    "DELIVERY_STAFF",
    "SECURITY_STAFF",
]


class StaffUserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    role: StaffRole = "CLEANING_STAFF"


class StaffUserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    role: StaffRole | None = None
    is_active: bool | None = None


class StaffUserResponse(BaseModel):
    id: int
    name: str
    email: str | None
    phone: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
