from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from grow8_common.models import UserAccount, UserRole
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.dependencies.db import get_db
from app.repositories import user_repository

_bearer = HTTPBearer(auto_error=False, description="JWT from POST /api/v1/auth/login")

Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
DbSession = Annotated[Session, Depends(get_db)]


def _user_from_token(session: Session, token: str) -> UserAccount:
    try:
        claims = decode_access_token(token)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise UnauthorizedError("Invalid or expired token", code="INVALID_TOKEN") from exc
    user = user_repository.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired token", code="INVALID_TOKEN")
    return user


def get_current_user(session: DbSession, credentials: Credentials) -> UserAccount:
    if credentials is None:
        raise UnauthorizedError("Authentication required", code="AUTH_REQUIRED")
    return _user_from_token(session, credentials.credentials)


def get_optional_user(session: DbSession, credentials: Credentials) -> UserAccount | None:
    """For public endpoints that show more to an authenticated owner."""
    if credentials is None:
        return None
    return _user_from_token(session, credentials.credentials)


def require_roles(*roles: UserRole) -> Callable[[UserAccount], UserAccount]:
    def guard(user: Annotated[UserAccount, Depends(get_current_user)]) -> UserAccount:
        if user.role not in roles:
            raise ForbiddenError(
                f"This action requires role: {', '.join(r.value for r in roles)}",
                code="ROLE_FORBIDDEN",
            )
        return user

    return guard


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]
OptionalUser = Annotated[UserAccount | None, Depends(get_optional_user)]
CurrentCreator = Annotated[UserAccount, Depends(require_roles(UserRole.CREATOR))]
