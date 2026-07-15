from sqlalchemy import func, select

from app.models.city import City
from app.repositories.base import BaseRepository


class CityRepository(BaseRepository):
    def get(self, city_id: int) -> City | None:
        return self.db.get(City, city_id)

    def get_by_name(self, name: str, *, exclude_id: int | None = None) -> City | None:
        statement = select(City).where(func.lower(City.name) == name.casefold())
        if exclude_id is not None:
            statement = statement.where(City.id != exclude_id)
        return self.db.scalar(statement.limit(1))

    def get_active_by_ids(self, city_ids: list[int]) -> list[City]:
        return self.db.scalars(select(City).where(City.id.in_(city_ids), City.is_active.is_(True))).all()

    def list(self, *, include_inactive: bool, page: int, page_size: int) -> tuple[int, list[City]]:
        filters = [] if include_inactive else [City.is_active.is_(True)]
        total = self.db.scalar(select(func.count(City.id)).where(*filters)) or 0
        cities = self.db.scalars(
            select(City)
            .where(*filters)
            .order_by(City.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return total, cities
