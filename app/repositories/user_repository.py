from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.constants import UserRole
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()).limit(1))

    def get_admin(self) -> User | None:
        return self.db.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.created_at).limit(1))

    def get_editor(self, editor_id: str) -> User | None:
        return (
            self.db.execute(
                select(User)
                .where(User.id == editor_id, User.role == UserRole.EDITOR)
                .options(selectinload(User.assigned_cities))
            )
            .unique()
            .scalar_one_or_none()
        )

    def list_editors(self, *, is_active: bool | None, page: int, page_size: int) -> tuple[int, list[User]]:
        filters = [User.role == UserRole.EDITOR]
        if is_active is not None:
            filters.append(User.is_active.is_(is_active))
        total = self.db.scalar(select(func.count(User.id)).where(*filters)) or 0
        users = (
            self.db.execute(
                select(User)
                .where(*filters)
                .options(selectinload(User.assigned_cities))
                .order_by(User.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .unique()
            .scalars()
            .all()
        )
        return total, users
