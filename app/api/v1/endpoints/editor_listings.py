from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_editor_or_admin
from app.core.constants import ListingStatus, UserRole
from app.db.session import get_db
from app.models.listing import Listing
from app.models.user import User
from app.schemas.listing import (
    ImageCoverUpdate,
    ListingCreate,
    ListingImageRead,
    ListingInternalRead,
    ListingUpdate,
    PaginatedInternalListings,
)
from app.services.listing_service import ListingService


router = APIRouter(prefix="/editor/listings", tags=["editor listings"])


def _listing_for_mutation(service: ListingService, listing_id: str, actor: User) -> Listing:
    """Admins may mutate every listing; editors remain limited to editable own listings."""
    if actor.role == UserRole.ADMIN:
        return service.get_or_404(listing_id)
    return service.get_editable_for_editor(listing_id, actor)


@router.post("", response_model=ListingInternalRead, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_editor_or_admin),
) -> dict:
    service = ListingService(db)
    if actor.role == UserRole.ADMIN:
        return service.to_internal_dict(service.create_for_admin(payload, actor))
    return service.to_internal_dict(service.create_for_editor(payload, actor))


@router.get("", response_model=PaginatedInternalListings)
def list_listings(
    status_filter: ListingStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_editor_or_admin),
) -> dict:
    service = ListingService(db)
    if actor.role == UserRole.ADMIN:
        total, listings = service.list_for_admin(
            status_filter=status_filter,
            submitted_by_id=None,
            city_id=None,
            page=page,
            page_size=page_size,
        )
    else:
        total, listings = service.list_for_editor(actor, status_filter=status_filter, page=page, page_size=page_size)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [service.to_internal_dict(item) for item in listings],
    }


@router.get("/{listing_id}", response_model=ListingInternalRead)
def get_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_editor_or_admin),
) -> dict:
    service = ListingService(db)
    listing = (
        service.get_or_404(listing_id)
        if actor.role == UserRole.ADMIN
        else service.get_for_editor(listing_id, actor)
    )
    return service.to_internal_dict(listing)


@router.patch("/{listing_id}", response_model=ListingInternalRead)
def update_listing(
    listing_id: str,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_editor_or_admin),
) -> dict:
    service = ListingService(db)
    if actor.role == UserRole.ADMIN:
        return service.to_internal_dict(service.update_for_admin(listing_id, payload, actor))
    return service.to_internal_dict(service.update_for_editor(listing_id, payload, actor))


@router.post("/{listing_id}/images", response_model=ListingInternalRead)
async def upload_images(
    listing_id: str,
    files: list[UploadFile] = File(...),
    cover_index: int | None = Form(default=None),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_editor_or_admin),
) -> dict:
    service = ListingService(db)
    listing = _listing_for_mutation(service, listing_id, actor)
    listing = await service.add_images(listing, files, cover_index)
    return service.to_internal_dict(listing)


@router.patch("/{listing_id}/images/{image_id}", response_model=ListingImageRead)
def set_cover_image(
    listing_id: str,
    image_id: str,
    _: ImageCoverUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_editor_or_admin),
) -> dict:
    service = ListingService(db)
    return service.image_to_dict(service.set_cover_image(_listing_for_mutation(service, listing_id, actor), image_id))


@router.delete("/{listing_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    listing_id: str,
    image_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_editor_or_admin),
) -> Response:
    service = ListingService(db)
    service.delete_image(_listing_for_mutation(service, listing_id, actor), image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
