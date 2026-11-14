from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RestaurantTableCreate(BaseModel):
    table_number: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=100)
    zone_coordinates: dict | list | None = None
    camera_source_id: int | None = Field(default=None, gt=0)


class RestaurantTableUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    zone_coordinates: dict | list | None = None
    camera_source_id: int | None = Field(default=None, gt=0)


class RestaurantTableResponse(BaseModel):
    id: int
    table_number: str
    name: str
    status: str
    zone_coordinates: dict | list | None
    camera_source_id: int | None
    last_status_changed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
