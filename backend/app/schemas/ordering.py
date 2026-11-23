from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    category: str = Field(min_length=2, max_length=80)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    size_prices: dict[str, Decimal] = Field(default_factory=dict)
    image_url: str | None = Field(default=None, max_length=500)
    ingredients: list[str] = Field(default_factory=list, max_length=50)
    allergens: list[str] = Field(default_factory=list, max_length=30)
    spice_level: Literal["MILD", "MEDIUM", "HOT", "EXTRA_HOT"] = "MILD"
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    category: str | None = Field(default=None, min_length=2, max_length=80)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    size_prices: dict[str, Decimal] | None = None
    image_url: str | None = Field(default=None, max_length=500)
    ingredients: list[str] | None = Field(default=None, max_length=50)
    allergens: list[str] | None = None
    spice_level: Literal["MILD", "MEDIUM", "HOT", "EXTRA_HOT"] | None = None
    is_available: bool | None = None


class MenuItemResponse(BaseModel):
    id: int
    name: str
    description: str | None
    category: str
    price: Decimal
    size_prices: dict[str, Decimal]
    image_url: str | None
    ingredients: list[str]
    allergens: list[str]
    spice_level: str
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class OrderItemCreate(BaseModel):
    menu_item_id: int
    size: str | None = Field(default=None, min_length=1, max_length=30)
    quantity: int = Field(ge=1, le=30)
    notes: str | None = Field(default=None, max_length=300)


class OrderCreate(BaseModel):
    table_id: int
    customer_name: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    customer_allergies: list[str] = Field(default_factory=list, max_length=20)
    allergy_notes: str | None = Field(default=None, max_length=500)
    items: list[OrderItemCreate] = Field(min_length=1, max_length=30)


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int | None
    item_name: str
    unit_price: Decimal
    size: str | None
    quantity: int
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    order_number: str
    table_id: int
    customer_name: str | None
    notes: str | None
    customer_allergies: list[str]
    allergy_notes: str | None
    status: str
    eating_completed_at: datetime | None = None
    payment_method: str | None = None
    payment_provider: str | None = None
    payment_status: str = "UNPAID"
    payment_requested_at: datetime | None = None
    payment_confirmed_at: datetime | None = None
    total_amount: Decimal
    created_at: datetime
    items: list[OrderItemResponse]

    model_config = ConfigDict(from_attributes=True)


class OrderCreatedResponse(OrderResponse):
    public_token: str


class OrderStatusUpdate(BaseModel):
    status: Literal["PREPARING", "READY", "SERVED", "CANCELLED"]

class SharedCartItemChange(BaseModel):
    menu_item_id: int
    size: str | None = Field(default=None, min_length=1, max_length=30)
    quantity_delta: int = Field(ge=-30, le=30)
    notes: str | None = Field(default=None, max_length=300)


class OrderFeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback: str | None = Field(default=None, max_length=1000)


class SharedCartSubmit(BaseModel):
    customer_name: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    customer_allergies: list[str] = Field(default_factory=list, max_length=20)
    allergy_notes: str | None = Field(default=None, max_length=500)

