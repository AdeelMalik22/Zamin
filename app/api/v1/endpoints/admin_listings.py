from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.core.constants import ListingStatus
from app.db.session import get_db
from app.models.user import User
from app.schemas.listing import ImageCoverUpdate, ListingCreate, ListingImageRead, ListingInternalRead, PaginatedInternalListings, RejectListing
from app.services.listing_service import ListingService


router = APIRouter(prefix="/admin/listings", tags=["admin listings"])


@router.post("", response_model=ListingInternalRead, status_code=status.HTTP_201_CREATED)
def create_admin_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict:
    service = ListingService(db)
    return service.to_internal_dict(service.create_for_admin(payload, admin))


@router.get("", response_model=PaginatedInternalListings)
def list_admin_listings(
    status_filter: ListingStatus | None = Query(None, alias="status"),
    submitted_by_id: str | None = Query(None),
    city_id: int | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    service = ListingService(db)
    total, listings = service.list_for_admin(
        status_filter=status_filter,
        submitted_by_id=submitted_by_id,
        city_id=city_id,
        page=page,
        page_size=page_size,
    )
    return {"page": page, "page_size": page_size, "total": total, "items": [service.to_internal_dict(item) for item in listings]}


@router.get("/{listing_id}", response_model=ListingInternalRead)
def get_admin_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    service = ListingService(db)
    return service.to_internal_dict(service.get_or_404(listing_id))


@router.post("/{listing_id}/approve", response_model=ListingInternalRead)
def approve_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict:
    service = ListingService(db)
    return service.to_internal_dict(service.approve(listing_id, admin))


@router.post("/{listing_id}/reject", response_model=ListingInternalRead)
def reject_listing(
    listing_id: str,
    payload: RejectListing,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict:
    service = ListingService(db)
    return service.to_internal_dict(service.reject(listing_id, payload.reason, admin))


@router.post("/{listing_id}/images", response_model=ListingInternalRead)
async def upload_images(
    listing_id: str,
    files: list[UploadFile] = File(...),
    cover_index: int | None = Form(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    service = ListingService(db)
    listing = await service.add_images(service.get_or_404(listing_id), files, cover_index)
    return service.to_internal_dict(listing)


@router.patch("/{listing_id}/images/{image_id}", response_model=ListingImageRead)
def set_cover_image(
    listing_id: str,
    image_id: str,
    _: ImageCoverUpdate,
    db: Session = Depends(get_db),
    __: User = Depends(get_current_admin),
) -> dict:
    service = ListingService(db)
    return service.image_to_dict(service.set_cover_image(service.get_or_404(listing_id), image_id))


@router.delete("/{listing_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    listing_id: str,
    image_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> Response:
    service = ListingService(db)
    service.delete_image(service.get_or_404(listing_id), image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
