from app.core.constants import UserRole
from app.schemas.city import CityCreate
from app.schemas.user import EditorCreate, EditorUpdate
from app.services.city_service import CityService
from app.services.user_service import UserService


def test_admin_can_create_and_update_a_city_scoped_editor(db):
    city = CityService(db).create(CityCreate(name="Lahore", province_or_region="Punjab"))
    service = UserService(db)
    editor, initial_password = service.create_editor(
        EditorCreate(
            full_name="Ayesha Agent",
            email="ayesha@example.com",
            phone_number="+923111234567",
            assigned_city_ids=[city.id],
        )
    )

    assert editor.role == UserRole.EDITOR
    assert initial_password
    updated = service.update_editor(editor.id, EditorUpdate(is_active=False))
    assert updated.is_active is False
