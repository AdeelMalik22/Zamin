from datetime import timedelta
from typing import TYPE_CHECKING, Any

import bcrypt
import jwt

from app.core.config import settings
from app.exceptions.custom_exceptions import UnauthorizedError
from app.utils.helpers import utc_now
from app.utils.validators import validate_password

if TYPE_CHECKING:
    from app.models.user import User


def hash_password(password: str) -> str:
    validate_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_token(user: "User", token_type: str, expires_delta: timedelta) -> str:
    now = utc_now()
    payload = {
        "sub": user.id,
        "role": user.role.value,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("invalid or expired token") from exc
    if payload.get("type") != expected_type or not isinstance(payload.get("sub"), str):
        raise UnauthorizedError("invalid token type")
    return payload
