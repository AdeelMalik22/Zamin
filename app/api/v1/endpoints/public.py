from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import ListingStatus, SearchMode
from app.db.session import get_db
from app.exceptions.custom_exceptions import NotFoundError
from app.schemas.listing import PaginatedPublicListings, PublicListingDetail
from app.services.listing_service import ListingService
from app.services.search_service import SearchService


router = APIRouter(prefix="/listings", tags=["public"])


@router.get("", response_model=PaginatedPublicListings)
def search_listings(
    city: str | None = Query(default=None, min_length=1, max_length=120),
    city_id: int | None = Query(default=None, gt=0),
    q: str | None = Query(default=None, max_length=100),
    search_mode: SearchMode = Query(default=SearchMode.CONTAINS),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    cleaned_city = city.strip() if city else None
    cleaned_query = q.strip() if q else None
    if cleaned_query == "":
        cleaned_query = None
    total, listings = SearchService(db).search(
        city=cleaned_city,
        city_id=city_id,
        query=cleaned_query,
        search_mode=search_mode,
        page=page,
        page_size=page_size,
    )
    listing_service = ListingService(db)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "search_mode": search_mode,
        "items": [listing_service.to_public_dict(listing) for listing in listings],
    }


@router.get("/{listing_id}", response_model=PublicListingDetail)
def get_listing(listing_id: str, db: Session = Depends(get_db)) -> dict:
    service = ListingService(db)
    listing = service.get_or_404(listing_id)
    if listing.status != ListingStatus.APPROVED:
        raise NotFoundError("listing not found")
    return service.to_public_dict(listing, include_detail=True)
