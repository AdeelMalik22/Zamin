from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import EditorCreate, EditorCreatedRead, EditorRead, EditorUpdate, PaginatedEditors
from app.services.user_service import UserService, editor_to_dict


router = APIRouter(prefix="/admin/editors", tags=["admin editors"])


@router.post("", response_model=EditorCreatedRead, status_code=status.HTTP_201_CREATED)
def create_editor(
    payload: EditorCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    editor, temporary_password = UserService(db).create_editor(payload)
    result = editor_to_dict(editor)
    result["temporary_password"] = temporary_password
    return result


@router.get("", response_model=PaginatedEditors)
def list_editors(
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    total, editors = UserService(db).list_editors(is_active=is_active, page=page, page_size=page_size)
    return {"page": page, "page_size": page_size, "total": total, "items": [editor_to_dict(editor) for editor in editors]}


@router.patch("/{editor_id}", response_model=EditorRead)
def update_editor(
    editor_id: str,
    payload: EditorUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    return editor_to_dict(UserService(db).update_editor(editor_id, payload))


@router.delete("/{editor_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_editor(
    editor_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> Response:
    UserService(db).deactivate_editor(editor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
