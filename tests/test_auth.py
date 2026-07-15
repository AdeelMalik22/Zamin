from app.core.security import decode_token
from app.services.auth_service import AuthService


def test_admin_can_log_in_and_refresh_token(db):
    service = AuthService(db)
    admin = service.seed_admin_if_missing(
        email="admin@example.com",
        password="StrongPass123!",
        full_name="Platform Admin",
        phone_number="+923001234567",
    )

    tokens = service.login("admin@example.com", "StrongPass123!")
    assert decode_token(tokens["access_token"], "access")["sub"] == admin.id

    refreshed = service.refresh(tokens["refresh_token"])
    assert decode_token(refreshed["access_token"], "access")["sub"] == admin.id
