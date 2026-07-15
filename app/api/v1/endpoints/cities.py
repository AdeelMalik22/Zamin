from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.city import CityCreate, CityRead, CityUpdate, PaginatedCities
from app.services.city_service import CityService, city_to_dict


router = APIRouter(tags=["cities"])


@router.post("/admin/cities", response_model=CityRead, status_code=status.HTTP_201_CREATED)
def create_city(
    payload: CityCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    return city_to_dict(CityService(db).create(payload))


@router.get("/admin/cities", response_model=PaginatedCities)
def list_admin_cities(
    include_inactive: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    total, cities = CityService(db).list(include_inactive=include_inactive, page=page, page_size=page_size)
    return {"page": page, "page_size": page_size, "total": total, "items": [city_to_dict(city) for city in cities]}


@router.patch("/admin/cities/{city_id}", response_model=CityRead)
def update_city(
    city_id: int,
    payload: CityUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    return city_to_dict(CityService(db).update(city_id, payload))


@router.get("/cities", response_model=PaginatedCities, tags=["public"])
def list_public_cities(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    total, cities = CityService(db).list(include_inactive=False, page=page, page_size=page_size)
    return {"page": page, "page_size": page_size, "total": total, "items": [city_to_dict(city) for city in cities]}
