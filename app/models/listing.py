from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ListingStatus, PropertyType, enum_values
from app.db.base import Base
from app.utils.helpers import new_uuid, utc_now

if TYPE_CHECKING:
    from app.models.city import City
    from app.models.user import User


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        Index("ix_listings_status_city_created", "status", "city_id", "created_at"),
        Index("ix_listings_address", "address"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), index=True, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    property_type: Mapped[PropertyType] = mapped_column(
        SAEnum(PropertyType, native_enum=False, values_callable=enum_values), nullable=False
    )
    status: Mapped[ListingStatus] = mapped_column(
        SAEnum(ListingStatus, native_enum=False, values_callable=enum_values),
        default=ListingStatus.PENDING,
        index=True,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contact_override_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    city: Mapped["City"] = relationship("City", back_populates="listings")
    submitted_by: Mapped["User"] = relationship(
        "User", back_populates="submitted_listings", foreign_keys=[submitted_by_id]
    )
    reviewed_by: Mapped["User | None"] = relationship(
        "User", back_populates="reviewed_listings", foreign_keys=[reviewed_by_id]
    )
    images: Mapped[list["ListingImage"]] = relationship(
        "ListingImage", back_populates="listing", cascade="all, delete-orphan", order_by="ListingImage.uploaded_at"
    )
    status_history: Mapped[list["ListingStatusHistory"]] = relationship(
        "ListingStatusHistory",
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="ListingStatusHistory.changed_at",
    )


class ListingImage(Base):
    __tablename__ = "listing_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True, nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    listing: Mapped[Listing] = relationship("Listing", back_populates="images")


class ListingStatusHistory(Base):
    __tablename__ = "listing_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True, nullable=False)
    from_status: Mapped[ListingStatus | None] = mapped_column(
        SAEnum(ListingStatus, native_enum=False, values_callable=enum_values), nullable=True
    )
    to_status: Mapped[ListingStatus] = mapped_column(
        SAEnum(ListingStatus, native_enum=False, values_callable=enum_values), nullable=False
    )
    changed_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    listing: Mapped[Listing] = relationship("Listing", back_populates="status_history")
    changed_by: Mapped["User"] = relationship("User", back_populates="status_changes")
