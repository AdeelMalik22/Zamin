from datetime import datetime, timezone
import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.custom_exceptions import ConflictError, ValidationAppError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


def commit_or_raise(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(message) from exc


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def validate_regex_pattern(pattern: str) -> None:
    if len(pattern) > 80:
        raise ValidationAppError("regex query is too long")
    if re.search(r"\\[1-9]|\(\?<|\(\?P=", pattern):
        raise ValidationAppError("unsupported regex construct")
    try:
        re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise ValidationAppError(f"invalid regex: {exc.msg}") from exc
