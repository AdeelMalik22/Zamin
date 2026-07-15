from datetime import datetime

from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.constants import UserRole
from app.schemas.city import CityRead
from app.schemas.common import APIModel
from app.utils.validators import clean_required_text, normalize_phone, validate_password


class EditorCreate(APIModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone_number: str = Field(min_length=7, max_length=32)
    assigned_city_ids: list[int] = Field(min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=72)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return clean_required_text(value, "full_name")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("password")
    @classmethod
    def validate_initial_password(cls, value: str | None) -> str | None:
        return validate_password(value) if value is not None else None


class EditorUpdate(APIModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, min_length=7, max_length=32)
    assigned_city_ids: list[int] | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)

    @field_validator("full_name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        return clean_required_text(value, "full_name") if value is not None else None

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value is not None else None

    @field_validator("phone_number")
    @classmethod
    def validate_optional_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value is not None else None

    @field_validator("password")
    @classmethod
    def validate_optional_password(cls, value: str | None) -> str | None:
        return validate_password(value) if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "EditorUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        for field_name in ("full_name", "email", "phone_number", "assigned_city_ids", "is_active", "password"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class EditorRead(APIModel):
    id: str
    full_name: str
    email: str
    phone_number: str
    is_active: bool
    assigned_cities: list[CityRead]
    created_at: datetime
    updated_at: datetime


class EditorCreatedRead(EditorRead):
    temporary_password: str


class CurrentUserRead(APIModel):
    id: str
    full_name: str
    email: str
    phone_number: str
    role: UserRole
    is_active: bool
    assigned_cities: list[CityRead]


class PaginatedEditors(APIModel):
    page: int
    page_size: int
    total: int
    items: list[EditorRead]
