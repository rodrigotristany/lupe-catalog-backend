import re
from pydantic import BaseModel, field_validator

WHATSAPP_REGEX = re.compile(r"^\+[0-9]{7,15}$")


class SettingsResponse(BaseModel):
    store_name: str
    whatsapp_number: str
    currency_symbol: str
    default_language: str

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    store_name: str | None = None
    whatsapp_number: str | None = None
    currency_symbol: str | None = None
    default_language: str | None = None

    @field_validator("whatsapp_number")
    @classmethod
    def whatsapp_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not WHATSAPP_REGEX.match(v):
            raise ValueError("whatsapp_number must be in international format, e.g. +5493534000000")
        return v

    @field_validator("currency_symbol")
    @classmethod
    def currency_symbol_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) > 5:
            raise ValueError("currency_symbol must be 5 characters or fewer")
        return v

    @field_validator("default_language")
    @classmethod
    def language_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("es", "en"):
            raise ValueError("default_language must be 'es' or 'en'")
        return v
