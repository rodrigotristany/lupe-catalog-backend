from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.schemas.category import CategoryResponse


class ProductImageResponse(BaseModel):
    id: int
    image_path: str
    sort_order: int

    model_config = {"from_attributes": True}


class ProductBase(BaseModel):
    name_es: str
    name_en: str
    description_es: str = ""
    description_en: str = ""
    price: Decimal
    category_id: int | None = None
    is_active: bool = True

    @field_validator("name_es", "name_en")
    @classmethod
    def name_length(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) > 255:
            raise ValueError("Name cannot exceed 255 characters")
        return v

    @field_validator("price")
    @classmethod
    def price_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Price must be >= 0")
        # Enforce max 2 decimal places
        if v != v.quantize(Decimal("0.01")):
            raise ValueError("Price may have at most 2 decimal places")
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name_es: str | None = None
    name_en: str | None = None
    description_es: str | None = None
    description_en: str | None = None
    price: Decimal | None = None
    category_id: int | None = None
    is_active: bool | None = None

    @field_validator("name_es", "name_en")
    @classmethod
    def name_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) > 255:
            raise ValueError("Name cannot exceed 255 characters")
        return v

    @field_validator("price")
    @classmethod
    def price_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if v < 0:
            raise ValueError("Price must be >= 0")
        if v != v.quantize(Decimal("0.01")):
            raise ValueError("Price may have at most 2 decimal places")
        return v


class ProductListItem(BaseModel):
    id: int
    name_es: str
    name_en: str
    description_es: str
    description_en: str
    price: str
    category: CategoryResponse | None
    primary_image: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductDetail(BaseModel):
    id: int
    name_es: str
    name_en: str
    description_es: str
    description_en: str
    price: str
    category: CategoryResponse | None
    images: list[ProductImageResponse]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductHistoryResponse(BaseModel):
    id: int
    action: str
    snapshot: dict
    changed_by: str
    changed_at: datetime

    model_config = {"from_attributes": True}
