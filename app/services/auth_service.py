from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import UserRole
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db.session import SessionLocal
from app.exceptions.custom_exceptions import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.helpers import commit_or_raise, new_uuid
from app.utils.validators import clean_required_text, normalize_phone, validate_password


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def login(self, email: str, password: str) -> dict:
        user = self.users.get_by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("invalid email or password")
        return self._token_pair(user)

    def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token, "refresh")
        user = self.users.get_by_id(payload["sub"])
        if user is None or not user.is_active:
            raise UnauthorizedError("account is unavailable")
        return self._token_pair(user)

    def _token_pair(self, user: User) -> dict:
        return {
            "access_token": create_token(user, "access", timedelta(minutes=settings.access_token_minutes)),
            "refresh_token": create_token(user, "refresh", timedelta(days=settings.refresh_token_days)),
            "token_type": "bearer",
            "expires_in": settings.access_token_minutes * 60,
        }

    def seed_admin_if_missing(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        phone_number: str,
    ) -> User:
        validate_password(password)
        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("a valid admin email is required")
        existing_admin = self.users.get_admin()
        if existing_admin is not None:
            return existing_admin
        account_with_email = self.users.get_by_email(normalized_email)
        if account_with_email is not None:
            raise ConflictError("the selected admin email is already assigned to another account")
        admin = User(
            id=new_uuid(),
            full_name=clean_required_text(full_name, "full_name"),
            email=normalized_email,
            phone_number=normalize_phone(phone_number),
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.db.add(admin)
        commit_or_raise(self.db, "unable to seed admin")
        return admin


def seed_admin(
    email: str,
    password: str,
    full_name: str = "Platform Admin",
    phone_number: str = "+10000000000",
) -> User:
    with SessionLocal() as db:
        return AuthService(db).seed_admin_if_missing(
            email=email,
            password=password,
            full_name=full_name,
            phone_number=phone_number,
        )


def bootstrap_admin_from_environment() -> None:
    if settings.admin_password:
        seed_admin(
            email=settings.admin_email,
            password=settings.admin_password,
            full_name=settings.admin_full_name,
            phone_number=settings.admin_phone_number,
        )
