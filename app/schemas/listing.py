from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.core.constants import ListingStatus, PropertyType, SearchMode
from app.schemas.city import CityRead
from app.schemas.common import APIModel
from app.utils.validators import clean_required_text, normalize_phone


class ListingCreate(APIModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=1, max_length=20_000)
    city_id: int = Field(gt=0)
    address: str = Field(min_length=3, max_length=1_000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    property_type: PropertyType
    contact_override_phone: str | None = Field(default=None, min_length=7, max_length=32)

    @field_validator("title", "description", "address")
    @classmethod
    def clean_listing_text(cls, value: str) -> str:
        return clean_required_text(value, "listing field")

    @field_validator("contact_override_phone")
    @classmethod
    def validate_optional_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value is not None else None


class ListingUpdate(APIModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=20_000)
    city_id: int | None = Field(default=None, gt=0)
    address: str | None = Field(default=None, min_length=3, max_length=1_000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    property_type: PropertyType | None = None
    contact_override_phone: str | None = Field(default=None, min_length=7, max_length=32)

    @field_validator("title", "description", "address")
    @classmethod
    def clean_optional_listing_text(cls, value: str | None) -> str | None:
        return clean_required_text(value, "listing field") if value is not None else None

    @field_validator("contact_override_phone")
    @classmethod
    def validate_optional_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "ListingUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        for field_name in ("title", "description", "city_id", "address", "property_type"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class RejectListing(APIModel):
    reason: str | None = Field(default=None, min_length=5, max_length=1_000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str | None) -> str | None:
        return clean_required_text(value, "reason") if value is not None else None


class ImageCoverUpdate(APIModel):
    is_cover: Literal[True] = True


class ListingImageRead(APIModel):
    id: str
    image_url: str
    is_cover: bool
    uploaded_at: datetime


class ListingActorRead(APIModel):
    id: str
    full_name: str
    phone_number: str


class ListingStatusHistoryRead(APIModel):
    from_status: ListingStatus | None
    to_status: ListingStatus
    reason: str | None
    changed_at: datetime
    changed_by: ListingActorRead


class PublicListingSummary(APIModel):
    id: str
    title: str
    city: CityRead
    address: str
    price: Decimal | None
    property_type: PropertyType
    contact_phone: str | None
    cover_image: ListingImageRead | None
    created_at: datetime


class PublicListingDetail(PublicListingSummary):
    description: str
    images: list[ListingImageRead]
    updated_at: datetime


class ListingInternalRead(PublicListingDetail):
    status: ListingStatus
    rejection_reason: str | None
    contact_override_phone: str | None
    submitted_by: ListingActorRead
    reviewed_by: ListingActorRead | None
    reviewed_at: datetime | None
    status_history: list[ListingStatusHistoryRead]


class PaginatedPublicListings(APIModel):
    page: int
    page_size: int
    total: int
    search_mode: SearchMode
    items: list[PublicListingSummary]


class PaginatedInternalListings(APIModel):
    page: int
    page_size: int
    total: int
    items: list[ListingInternalRead]
