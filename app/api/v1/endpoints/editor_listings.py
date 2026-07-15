from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_editor
from app.core.constants import ListingStatus
from app.db.session import get_db
from app.models.user import User
from app.schemas.listing import ImageCoverUpdate, ListingCreate, ListingImageRead, ListingInternalRead, ListingUpdate, PaginatedInternalListings
from app.services.listing_service import ListingService


router = APIRouter(prefix="/editor/listings", tags=["editor listings"])


@router.post("", response_model=ListingInternalRead, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    editor: User = Depends(get_current_editor),
) -> dict:
    service = ListingService(db)
    return service.to_internal_dict(service.create_for_editor(payload, editor))


@router.get("", response_model=PaginatedInternalListings)
def list_listings(
    status_filter: ListingStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    editor: User = Depends(get_current_editor),
) -> dict:
    service = ListingService(db)
    total, listings = service.list_for_editor(editor, status_filter=status_filter, page=page, page_size=page_size)
    return {"page": page, "page_size": page_size, "total": total, "items": [service.to_internal_dict(item) for item in listings]}


@router.get("/{listing_id}", response_model=ListingInternalRead)
def get_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    editor: User = Depends(get_current_editor),
) -> dict:
    service = ListingService(db)
    return service.to_internal_dict(service.get_for_editor(listing_id, editor))


@router.patch("/{listing_id}", response_model=ListingInternalRead)
def update_listing(
    listing_id: str,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    editor: User = Depends(get_current_editor),
) -> dict:
    service = ListingService(db)
    return service.to_internal_dict(service.update_for_editor(listing_id, payload, editor))


@router.post("/{listing_id}/images", response_model=ListingInternalRead)
async def upload_images(
    listing_id: str,
    files: list[UploadFile] = File(...),
    cover_index: int | None = Form(default=None),
    db: Session = Depends(get_db),
    editor: User = Depends(get_current_editor),
) -> dict:
    service = ListingService(db)
    listing = service.get_editable_for_editor(listing_id, editor)
    listing = await service.add_images(listing, files, cover_index)
    return service.to_internal_dict(listing)


@router.patch("/{listing_id}/images/{image_id}", response_model=ListingImageRead)
def set_cover_image(
    listing_id: str,
    image_id: str,
    _: ImageCoverUpdate,
    db: Session = Depends(get_db),
    editor: User = Depends(get_current_editor),
) -> dict:
    service = ListingService(db)
    return service.image_to_dict(service.set_cover_image(service.get_editable_for_editor(listing_id, editor), image_id))


@router.delete("/{listing_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    listing_id: str,
    image_id: str,
    db: Session = Depends(get_db),
    editor: User = Depends(get_current_editor),
) -> Response:
    service = ListingService(db)
    service.delete_image(service.get_editable_for_editor(listing_id, editor), image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
