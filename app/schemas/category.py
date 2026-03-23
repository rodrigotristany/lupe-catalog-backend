from pydantic import BaseModel, field_validator


class CategoryBase(BaseModel):
    name_es: str
    name_en: str

    @field_validator("name_es", "name_en")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name_es: str | None = None
    name_en: str | None = None


class CategoryResponse(BaseModel):
    id: int
    name_es: str
    name_en: str
    slug: str

    model_config = {"from_attributes": True}
