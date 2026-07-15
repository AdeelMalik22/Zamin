from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.exceptions.custom_exceptions import UnauthorizedError
from app.middleware.rate_limit import login_rate_limiter
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.user import CurrentUserRead
from app.services.auth_service import AuthService
from app.services.city_service import city_to_dict


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    client_key = request.client.host if request.client else "unknown"
    login_rate_limiter.ensure_allowed(client_key)
    try:
        result = AuthService(db).login(str(payload.email), payload.password)
    except UnauthorizedError:
        login_rate_limiter.record_failure(client_key)
        raise
    login_rate_limiter.reset(client_key)
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> dict:
    return AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=CurrentUserRead)
def current_account(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "assigned_cities": [city_to_dict(city) for city in current_user.assigned_cities],
    }
