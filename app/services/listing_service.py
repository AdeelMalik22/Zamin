from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import ListingStatus
from app.exceptions.custom_exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.listing import Listing, ListingImage, ListingStatusHistory
from app.models.user import User
from app.repositories.listing_repository import ListingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.listing import ListingCreate, ListingUpdate
from app.services.city_service import CityService, city_to_dict
from app.services.storage_service import LocalListingStorage
from app.services.user_service import user_to_actor_dict
from app.utils.helpers import commit_or_raise, new_uuid, utc_now


class ListingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ListingRepository(db)
        self.city_service = CityService(db)
        self.users = UserRepository(db)
        self.storage = LocalListingStorage()

    def get_or_404(self, listing_id: str) -> Listing:
        listing = self.repository.get(listing_id)
        if listing is None:
            raise NotFoundError("listing not found")
        return listing

    def _ensure_editor_can_use_city(self, editor: User, city_id: int) -> None:
        allowed_city_ids = {city.id for city in editor.assigned_cities if city.is_active}
        if city_id not in allowed_city_ids:
            raise ForbiddenError("editors may only submit listings in their assigned cities")

    def _add_status_history(
        self,
        listing: Listing,
        from_status: ListingStatus | None,
        to_status: ListingStatus,
        actor: User,
        reason: str | None = None,
    ) -> None:
        self.db.add(
            ListingStatusHistory(
                listing_id=listing.id,
                from_status=from_status,
                to_status=to_status,
                changed_by_id=actor.id,
                reason=reason,
            )
        )

    def _create_listing(
        self,
        payload: ListingCreate,
        submitted_by: User,
        *,
        listing_status: ListingStatus,
        reviewed_by: User | None = None,
    ) -> Listing:
        return Listing(
            id=new_uuid(),
            title=payload.title,
            description=payload.description,
            city_id=payload.city_id,
            address=payload.address,
            price=payload.price,
            property_type=payload.property_type,
            status=listing_status,
            submitted_by_id=submitted_by.id,
            reviewed_by_id=reviewed_by.id if reviewed_by else None,
            reviewed_at=utc_now() if listing_status == ListingStatus.APPROVED else None,
            contact_override_phone=payload.contact_override_phone,
        )

    def create_for_editor(self, payload: ListingCreate, editor: User) -> Listing:
        self.city_service.get_active_or_error(payload.city_id)
        self._ensure_editor_can_use_city(editor, payload.city_id)
        listing = self._create_listing(payload, editor, listing_status=ListingStatus.PENDING)
        self.db.add(listing)
        self._add_status_history(listing, None, ListingStatus.PENDING, editor, "Submitted for review")
        commit_or_raise(self.db, "unable to create listing")
        return self.get_or_404(listing.id)

    def create_for_admin(self, payload: ListingCreate, admin: User) -> Listing:
        self.city_service.get_active_or_error(payload.city_id)
        listing = self._create_listing(
            payload,
            admin,
            listing_status=ListingStatus.APPROVED,
            reviewed_by=admin,
        )
        self.db.add(listing)
        self._add_status_history(listing, None, ListingStatus.APPROVED, admin, "Created and approved by admin")
        commit_or_raise(self.db, "unable to create listing")
        return self.get_or_404(listing.id)

    def list_for_admin(
        self,
        *,
        status_filter: ListingStatus | None,
        submitted_by_id: str | None,
        city_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[int, list[Listing]]:
        filters: list[Any] = []
        if status_filter is not None:
            filters.append(Listing.status == status_filter)
        if submitted_by_id is not None:
            filters.append(Listing.submitted_by_id == submitted_by_id)
        if city_id is not None:
            filters.append(Listing.city_id == city_id)
        return self.repository.list_internal(filters=filters, page=page, page_size=page_size)

    def list_for_editor(
        self,
        editor: User,
        *,
        status_filter: ListingStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[int, list[Listing]]:
        filters: list[Any] = [Listing.submitted_by_id == editor.id]
        if status_filter is not None:
            filters.append(Listing.status == status_filter)
        return self.repository.list_internal(filters=filters, page=page, page_size=page_size)

    def get_for_editor(self, listing_id: str, editor: User) -> Listing:
        listing = self.get_or_404(listing_id)
        if listing.submitted_by_id != editor.id:
            raise NotFoundError("listing not found")
        return listing

    def get_editable_for_editor(self, listing_id: str, editor: User) -> Listing:
        listing = self.get_for_editor(listing_id, editor)
        if listing.status not in (ListingStatus.PENDING, ListingStatus.REJECTED):
            raise ConflictError("approved listings cannot be changed by an editor")
        return listing

    def update_for_editor(self, listing_id: str, payload: ListingUpdate, editor: User) -> Listing:
        listing = self.get_editable_for_editor(listing_id, editor)
        changes = payload.model_dump(exclude_unset=True)
        if "city_id" in changes:
            self.city_service.get_active_or_error(changes["city_id"])
            self._ensure_editor_can_use_city(editor, changes["city_id"])
        for field_name, value in changes.items():
            setattr(listing, field_name, value)
        if listing.status == ListingStatus.REJECTED:
            listing.status = ListingStatus.PENDING
            listing.rejection_reason = None
            listing.reviewed_by_id = None
            listing.reviewed_at = None
            self._add_status_history(
                listing,
                ListingStatus.REJECTED,
                ListingStatus.PENDING,
                editor,
                "Edited and resubmitted",
            )
        commit_or_raise(self.db, "unable to update listing")
        return self.get_or_404(listing.id)

    def approve(self, listing_id: str, admin: User) -> Listing:
        listing = self.get_or_404(listing_id)
        if listing.status != ListingStatus.PENDING:
            raise ConflictError("only pending listings may be approved")
        listing.status = ListingStatus.APPROVED
        listing.rejection_reason = None
        listing.reviewed_by_id = admin.id
        listing.reviewed_at = utc_now()
        self._add_status_history(listing, ListingStatus.PENDING, ListingStatus.APPROVED, admin)
        commit_or_raise(self.db, "unable to approve listing")
        return self.get_or_404(listing.id)

    def reject(self, listing_id: str, reason: str | None, admin: User) -> Listing:
        listing = self.get_or_404(listing_id)
        if listing.status != ListingStatus.PENDING:
            raise ConflictError("only pending listings may be rejected")
        listing.status = ListingStatus.REJECTED
        listing.rejection_reason = reason
        listing.reviewed_by_id = admin.id
        listing.reviewed_at = utc_now()
        self._add_status_history(listing, ListingStatus.PENDING, ListingStatus.REJECTED, admin, reason)
        commit_or_raise(self.db, "unable to reject listing")
        return self.get_or_404(listing.id)

    async def add_images(self, listing: Listing, files: list[UploadFile], cover_index: int | None) -> Listing:
        if cover_index is not None and not 0 <= cover_index < len(files):
            raise ValidationAppError("cover_index is out of range")
        existing_images = self.repository.images_for_listing(listing.id)
        if len(existing_images) + len(files) > settings.max_images_per_listing:
            raise ValidationAppError(f"a listing may have at most {settings.max_images_per_listing} images")
        prepared = await self.storage.prepare_images(files)
        selected_cover_index = cover_index
        if selected_cover_index is None and not any(image.is_cover for image in existing_images):
            selected_cover_index = 0
        if selected_cover_index is not None:
            for image in existing_images:
                image.is_cover = False
        stored = self.storage.store_images(listing.id, prepared)
        try:
            for index, item in enumerate(stored):
                self.db.add(
                    ListingImage(
                        id=item.image_id,
                        listing_id=listing.id,
                        image_path=item.image_url,
                        is_cover=index == selected_cover_index,
                    )
                )
            commit_or_raise(self.db, "unable to save uploaded images")
        except Exception:
            self.db.rollback()
            for item in stored:
                item.disk_path.unlink(missing_ok=True)
            raise
        listing_id = listing.id
        self.db.expire_all()
        return self.get_or_404(listing_id)

    def delete_image(self, listing: Listing, image_id: str) -> None:
        image = self.repository.get_image(listing.id, image_id)
        if image is None:
            raise NotFoundError("image not found")
        was_cover = image.is_cover
        image_url = image.image_path
        self.db.delete(image)
        self.db.flush()
        if was_cover:
            next_image = self.repository.next_image_for_cover(listing.id)
            if next_image is not None:
                next_image.is_cover = True
        commit_or_raise(self.db, "unable to delete image")
        self.storage.delete_image(image_url)

    def set_cover_image(self, listing: Listing, image_id: str) -> ListingImage:
        image = self.repository.get_image(listing.id, image_id)
        if image is None:
            raise NotFoundError("image not found")
        for existing_image in self.repository.images_for_listing(listing.id):
            existing_image.is_cover = existing_image.id == image.id
        commit_or_raise(self.db, "unable to update image cover")
        return image

    def _resolve_contact_phone(self, listing: Listing) -> str | None:
        if listing.contact_override_phone:
            return listing.contact_override_phone
        if listing.submitted_by and listing.submitted_by.phone_number:
            return listing.submitted_by.phone_number
        admin = self.users.get_admin()
        return admin.phone_number if admin else None

    @staticmethod
    def _ordered_images(listing: Listing) -> list[ListingImage]:
        return sorted(listing.images, key=lambda image: (not image.is_cover, image.uploaded_at, image.id))

    @staticmethod
    def image_to_dict(image: ListingImage) -> dict:
        return {
            "id": image.id,
            "image_url": image.image_path,
            "is_cover": image.is_cover,
            "uploaded_at": image.uploaded_at,
        }

    def to_public_dict(self, listing: Listing, *, include_detail: bool = False) -> dict:
        images = [self.image_to_dict(image) for image in self._ordered_images(listing)]
        result = {
            "id": listing.id,
            "title": listing.title,
            "city": city_to_dict(listing.city),
            "address": listing.address,
            "price": listing.price,
            "property_type": listing.property_type,
            "contact_phone": self._resolve_contact_phone(listing),
            "cover_image": images[0] if images else None,
            "created_at": listing.created_at,
        }
        if include_detail:
            result.update({"description": listing.description, "images": images, "updated_at": listing.updated_at})
        return result

    def to_internal_dict(self, listing: Listing) -> dict:
        result = self.to_public_dict(listing, include_detail=True)
        result.update(
            {
                "status": listing.status,
                "rejection_reason": listing.rejection_reason,
                "contact_override_phone": listing.contact_override_phone,
                "submitted_by": user_to_actor_dict(listing.submitted_by),
                "reviewed_by": user_to_actor_dict(listing.reviewed_by) if listing.reviewed_by else None,
                "reviewed_at": listing.reviewed_at,
                "status_history": [
                    {
                        "from_status": change.from_status,
                        "to_status": change.to_status,
                        "reason": change.reason,
                        "changed_at": change.changed_at,
                        "changed_by": user_to_actor_dict(change.changed_by),
                    }
                    for change in sorted(listing.status_history, key=lambda change: (change.changed_at, change.id))
                ],
            }
        )
        return result
