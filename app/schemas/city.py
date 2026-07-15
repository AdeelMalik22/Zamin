from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel
from app.utils.validators import clean_required_text


class CityCreate(APIModel):
    name: str = Field(min_length=2, max_length=120)
    province_or_region: str = Field(min_length=2, max_length=120)

    @field_validator("name", "province_or_region")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return clean_required_text(value, "city field")


class CityUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    province_or_region: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None

    @field_validator("name", "province_or_region")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return clean_required_text(value, "city field") if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "CityUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        for field_name in ("name", "province_or_region", "is_active"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class CityRead(APIModel):
    id: int
    name: str
    province_or_region: str
    is_active: bool


class PaginatedCities(APIModel):
    page: int
    page_size: int
    total: int
    items: list[CityRead]
