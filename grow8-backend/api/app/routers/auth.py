from fastapi import APIRouter

from app.dependencies.auth import CurrentUser, DbSession
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserRead,
    UserUpdate,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: DbSession) -> TokenResponse:
    """Exchange email + password for a JWT."""
    return auth_service.login(session, body.email, body.password)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
def update_me(body: UserUpdate, session: DbSession, user: CurrentUser) -> UserRead:
    """Change your name (any role). Email can't be changed here."""
    return UserRead.model_validate(auth_service.update_me(session, user, body.full_name))


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    session: DbSession,
    user: CurrentUser,
) -> dict[str, str]:
    """Change the authenticated user's password."""
    auth_service.change_password(
        session=session,
        user=user,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return {"message": "Password changed successfully."}
