from sqlalchemy import Column, ForeignKey, Table

from app.db.base import Base


editor_cities = Table(
    "editor_cities",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("city_id", ForeignKey("cities.id", ondelete="RESTRICT"), primary_key=True),
)
