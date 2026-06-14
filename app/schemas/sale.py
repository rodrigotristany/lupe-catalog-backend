from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, field_validator


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be at least 1")
        return v


class SaleCreate(BaseModel):
    payment_method: str
    items: list[SaleItemCreate]

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("items must contain at least one product")
        return v


class SaleProductResponse(BaseModel):
    id: int
    product_id: int | None
    product_name_es: str
    product_name_en: str
    category_id: int | None
    category_name_es: str | None
    category_name_en: str | None
    price: Decimal
    quantity: int
    subtotal: Decimal

    model_config = {"from_attributes": True}


class SaleResponse(BaseModel):
    id: int
    payment_method: str
    total: Decimal
    created_at: datetime
    items: list[SaleProductResponse]

    model_config = {"from_attributes": True}
