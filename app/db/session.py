from collections.abc import Generator
from typing import Any
import re

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def sqlite_regexp(pattern: str | None, value: str | None) -> int:
    if pattern is None or value is None:
        return 0
    try:
        return int(re.search(str(pattern), str(value), re.IGNORECASE) is not None)
    except re.error:
        return 0


engine_options: dict[str, Any] = {"future": True}
if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
    if settings.database_url.endswith(":memory:"):
        engine_options["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **engine_options)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(dbapi_connection: Any, _: Any) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
        dbapi_connection.create_function("regexp", 2, sqlite_regexp)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
