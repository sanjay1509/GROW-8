from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import user_repository
from app.schemas.auth import TokenResponse, UserRead
from grow8_common.models import UserAccount

# Compared against when the email is unknown, so both failure paths cost a bcrypt check.
_DUMMY_HASH = hash_password("grow8-timing-equalizer")


def login(session: Session, email: str, password: str) -> TokenResponse:
    user = user_repository.get_by_email(session, email.strip().lower())
    password_ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not password_ok or not user.is_active:
        raise UnauthorizedError("Incorrect email or password", code="INVALID_CREDENTIALS")
    token, expires_in = create_access_token(user.user_id, user.role)
    return TokenResponse(
        access_token=token, expires_in=expires_in, user=UserRead.model_validate(user)
    )

def change_password(
    session: Session,
    user: UserAccount,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise UnauthorizedError(
            "Current password is incorrect",
            code="INVALID_CURRENT_PASSWORD",
        )

    if verify_password(new_password, user.password_hash):
        from app.core.exceptions import ValidationError
        raise ValidationError(
            "New password must differ from the current password",
            code="PASSWORD_UNCHANGED",
        )

    user.password_hash = hash_password(new_password)

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise