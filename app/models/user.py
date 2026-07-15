from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import UserRole, enum_values
from app.db.base import Base
from app.models.associations import editor_cities
from app.utils.helpers import new_uuid, utc_now

if TYPE_CHECKING:
    from app.models.city import City
    from app.models.listing import Listing, ListingStatusHistory


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False, values_callable=enum_values), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    assigned_cities: Mapped[list["City"]] = relationship(
        "City", secondary=editor_cities, back_populates="assigned_editors", order_by="City.name"
    )
    submitted_listings: Mapped[list["Listing"]] = relationship(
        "Listing", back_populates="submitted_by", foreign_keys="Listing.submitted_by_id"
    )
    reviewed_listings: Mapped[list["Listing"]] = relationship(
        "Listing", back_populates="reviewed_by", foreign_keys="Listing.reviewed_by_id"
    )
    status_changes: Mapped[list["ListingStatusHistory"]] = relationship(
        "ListingStatusHistory", back_populates="changed_by"
    )
