from grow8_common.models import UserRole
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import BCRYPT_MAX_BYTES, password_fits_bcrypt


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    # Not capped at 72 bytes: only the first 72 are compared, as bcrypt always did,
    # so a password set before the cap still signs in.
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    full_name: str
    role: UserRole


class UserUpdate(BaseModel):
    """PATCH /auth/me body, for every role. Email is the sign-in, so it can't be changed
    here (sending it is a 422 like any unknown field)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=150)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(
        min_length=8,
        max_length=BCRYPT_MAX_BYTES,
        description="8 characters to 72 bytes (UTF-8); accented letters and emoji take more "
        "than one byte",
    )

    @field_validator("new_password")
    @classmethod
    def _fits_bcrypt(cls, value: str) -> str:
        if not password_fits_bcrypt(value):
            raise ValueError(f"must be at most {BCRYPT_MAX_BYTES} bytes when UTF-8 encoded")
        return value
