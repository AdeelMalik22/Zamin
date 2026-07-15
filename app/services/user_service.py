import secrets

from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.security import hash_password
from app.exceptions.custom_exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import EditorCreate, EditorUpdate
from app.services.city_service import CityService, city_to_dict
from app.utils.helpers import commit_or_raise, new_uuid


def user_to_actor_dict(user: User) -> dict:
    return {"id": user.id, "full_name": user.full_name, "phone_number": user.phone_number}


def editor_to_dict(editor: User) -> dict:
    return {
        "id": editor.id,
        "full_name": editor.full_name,
        "email": editor.email,
        "phone_number": editor.phone_number,
        "is_active": editor.is_active,
        "assigned_cities": [city_to_dict(city) for city in sorted(editor.assigned_cities, key=lambda city: city.name.casefold())],
        "created_at": editor.created_at,
        "updated_at": editor.updated_at,
    }


def generate_temporary_password() -> str:
    return f"{secrets.token_urlsafe(12)}A1!"


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)
        self.city_service = CityService(db)

    def get_editor_or_404(self, editor_id: str) -> User:
        editor = self.repository.get_editor(editor_id)
        if editor is None:
            raise NotFoundError("editor not found")
        return editor

    def create_editor(self, payload: EditorCreate) -> tuple[User, str]:
        if self.repository.get_by_email(str(payload.email)) is not None:
            raise ConflictError("an account with this email already exists")
        assigned_cities = self.city_service.resolve_active_cities(payload.assigned_city_ids)
        temporary_password = payload.password or generate_temporary_password()
        editor = User(
            id=new_uuid(),
            full_name=payload.full_name,
            email=str(payload.email),
            phone_number=payload.phone_number,
            hashed_password=hash_password(temporary_password),
            role=UserRole.EDITOR,
            is_active=True,
            assigned_cities=assigned_cities,
        )
        self.db.add(editor)
        commit_or_raise(self.db, "unable to create editor")
        self.db.refresh(editor)
        return editor, temporary_password

    def update_editor(self, editor_id: str, payload: EditorUpdate) -> User:
        editor = self.get_editor_or_404(editor_id)
        changes = payload.model_dump(exclude_unset=True)
        if "email" in changes:
            existing = self.repository.get_by_email(str(changes["email"]))
            if existing is not None and existing.id != editor.id:
                raise ConflictError("an account with this email already exists")
        if "assigned_city_ids" in changes:
            editor.assigned_cities = self.city_service.resolve_active_cities(changes.pop("assigned_city_ids"))
        if "password" in changes:
            editor.hashed_password = hash_password(changes.pop("password"))
        for field_name, value in changes.items():
            setattr(editor, field_name, value)
        commit_or_raise(self.db, "unable to update editor")
        self.db.refresh(editor)
        return editor

    def deactivate_editor(self, editor_id: str) -> None:
        editor = self.get_editor_or_404(editor_id)
        editor.is_active = False
        commit_or_raise(self.db, "unable to deactivate editor")

    def list_editors(self, *, is_active: bool | None, page: int, page_size: int) -> tuple[int, list[User]]:
        return self.repository.list_editors(is_active=is_active, page=page, page_size=page_size)
