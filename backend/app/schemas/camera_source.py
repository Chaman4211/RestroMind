from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CameraSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    source_type: Literal["UPLOAD", "LIVE"]


class CameraSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    source_type: Literal["UPLOAD", "LIVE"] | None = None
    is_active: bool | None = None


class CameraSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
