from sqlalchemy.orm import Session

from app.exceptions.custom_exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.city import City
from app.repositories.city_repository import CityRepository
from app.schemas.city import CityCreate, CityUpdate
from app.utils.helpers import commit_or_raise


def city_to_dict(city: City) -> dict:
    return {
        "id": city.id,
        "name": city.name,
        "province_or_region": city.province_or_region,
        "is_active": city.is_active,
    }


class CityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CityRepository(db)

    def get_or_404(self, city_id: int) -> City:
        city = self.repository.get(city_id)
        if city is None:
            raise NotFoundError("city not found")
        return city

    def get_active_or_error(self, city_id: int) -> City:
        city = self.repository.get(city_id)
        if city is None or not city.is_active:
            raise ValidationAppError("city must be active")
        return city

    def resolve_active_cities(self, city_ids: list[int]) -> list[City]:
        unique_ids = list(dict.fromkeys(city_ids))
        cities = self.repository.get_active_by_ids(unique_ids)
        by_id = {city.id: city for city in cities}
        missing_ids = [city_id for city_id in unique_ids if city_id not in by_id]
        if missing_ids:
            raise ValidationAppError(f"unknown or inactive city IDs: {missing_ids}")
        return [by_id[city_id] for city_id in unique_ids]

    def create(self, payload: CityCreate) -> City:
        if self.repository.get_by_name(payload.name) is not None:
            raise ConflictError("a city with this name already exists")
        city = City(name=payload.name, province_or_region=payload.province_or_region)
        self.db.add(city)
        commit_or_raise(self.db, "unable to create city")
        self.db.refresh(city)
        return city

    def update(self, city_id: int, payload: CityUpdate) -> City:
        city = self.get_or_404(city_id)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and self.repository.get_by_name(changes["name"], exclude_id=city.id):
            raise ConflictError("a city with this name already exists")
        for field_name, value in changes.items():
            setattr(city, field_name, value)
        commit_or_raise(self.db, "unable to update city")
        self.db.refresh(city)
        return city

    def list(self, *, include_inactive: bool, page: int, page_size: int) -> tuple[int, list[City]]:
        return self.repository.list(include_inactive=include_inactive, page=page, page_size=page_size)
