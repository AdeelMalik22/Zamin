from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.security import decode_token
from app.db.session import get_db
from app.exceptions.custom_exceptions import ForbiddenError, UnauthorizedError
from app.models.user import User
from app.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("authentication required")
    payload = decode_token(credentials.credentials, "access")
    user = UserRepository(db).get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise UnauthorizedError("account is unavailable")
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError("admin access required")
    return current_user


def get_current_editor(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.EDITOR:
        raise ForbiddenError("editor access required")
    return current_user


def get_current_editor_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.ADMIN, UserRole.EDITOR):
        raise ForbiddenError("editor or admin access required")
    return current_user
