from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from grow8_common.models import UserRole

from app.core.config import JWT_ALGORITHM, get_api_settings

# bcrypt only ever uses the first 72 bytes of a password (ADR 0005).
BCRYPT_MAX_BYTES = 72


def _bcrypt_input(password: str) -> bytes:
    """What bcrypt actually sees: the UTF-8 bytes, cut at 72. bcrypt 4.x cuts silently;
    5.x raises instead, so cutting here keeps both versions verifying the same way."""
    return password.encode()[:BCRYPT_MAX_BYTES]


def password_fits_bcrypt(password: str) -> bool:
    return len(password.encode()) <= BCRYPT_MAX_BYTES


def hash_password(password: str) -> str:
    """Hash a new password. Raises ValueError if bcrypt would ignore part of it;
    request schemas reject such passwords first."""
    if not password_fits_bcrypt(password):
        raise ValueError(f"password longer than {BCRYPT_MAX_BYTES} bytes")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_input(password), password_hash.encode())
    except ValueError:  # malformed stored hash
        return False


def same_password(a: str, b: str) -> bool:
    """True if bcrypt can't tell the two apart (their first 72 bytes are equal)."""
    return _bcrypt_input(a) == _bcrypt_input(b)


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
