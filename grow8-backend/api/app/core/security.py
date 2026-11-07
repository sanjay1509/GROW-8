from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from grow8_common.models import UserRole

from app.core.config import JWT_ALGORITHM, get_api_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # malformed stored hash
        return False


def create_access_token(user_id: int, role: UserRole) -> tuple[str, int]:
    """Return (token, lifetime in seconds)."""
    settings = get_api_settings()
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(UTC)
    claims = {"sub": str(user_id), "role": role.value, "iat": now, "exp": now + lifetime}
    token = jwt.encode(claims, settings.effective_jwt_secret, algorithm=JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict[str, str]:
    """Raise jwt.PyJWTError if the token is invalid or expired."""
    return jwt.decode(
        token,
        get_api_settings().effective_jwt_secret,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "role", "exp"]},
    )
