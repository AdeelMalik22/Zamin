from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from app.models.listing import Listing, ListingImage, ListingStatusHistory
from app.repositories.base import BaseRepository


LISTING_LOAD_OPTIONS = (
    joinedload(Listing.city),
    joinedload(Listing.submitted_by),
    joinedload(Listing.reviewed_by),
    selectinload(Listing.images),
    selectinload(Listing.status_history).joinedload(ListingStatusHistory.changed_by),
)


class ListingRepository(BaseRepository):
    def get(self, listing_id: str) -> Listing | None:
        return (
            self.db.execute(select(Listing).where(Listing.id == listing_id).options(*LISTING_LOAD_OPTIONS))
            .unique()
            .scalar_one_or_none()
        )

    def get_image(self, listing_id: str, image_id: str) -> ListingImage | None:
        return self.db.scalar(
            select(ListingImage).where(ListingImage.id == image_id, ListingImage.listing_id == listing_id)
        )

    def get_by_submitter_and_title(self, submitted_by_id: str, title: str) -> Listing | None:
        return self.db.scalar(
            select(Listing).where(Listing.submitted_by_id == submitted_by_id, Listing.title == title).limit(1)
        )

    def list_internal(
        self,
        *,
        filters: list[Any],
        page: int,
        page_size: int,
    ) -> tuple[int, list[Listing]]:
        total = self.db.scalar(select(func.count(Listing.id)).where(*filters)) or 0
        listings = (
            self.db.execute(
                select(Listing)
                .where(*filters)
                .options(*LISTING_LOAD_OPTIONS)
                .order_by(Listing.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .unique()
            .scalars()
            .all()
        )
        return total, listings

    def next_image_for_cover(self, listing_id: str) -> ListingImage | None:
        return self.db.scalar(
            select(ListingImage)
            .where(ListingImage.listing_id == listing_id)
            .order_by(ListingImage.uploaded_at.asc(), ListingImage.id.asc())
            .limit(1)
        )

    def images_for_listing(self, listing_id: str) -> list[ListingImage]:
        return self.db.scalars(select(ListingImage).where(ListingImage.listing_id == listing_id)).all()
