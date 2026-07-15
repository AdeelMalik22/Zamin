from app.db.base import Base
from app.db.session import engine
from app.models import city, listing, user  # noqa: F401 - registers all metadata


def init_database() -> None:
    """Development bootstrap; production deployments should run Alembic migrations."""
    Base.metadata.create_all(bind=engine)
