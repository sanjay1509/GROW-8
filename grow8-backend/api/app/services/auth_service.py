from grow8_common.models import ContributorProfile, UserAccount, UserRole
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError, UnprocessableError
from app.core.security import (
    create_access_token,
    hash_password,
    same_password,
    verify_password,
)
from app.repositories import user_repository
from app.repositories.db_errors import duplicate_key
from app.schemas.auth import SignUpRequest, TokenResponse, UserRead

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


def register(session: Session, data: SignUpRequest) -> TokenResponse:
    """Create a contributor or creator account and sign the new user in."""
    user = UserAccount(
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole(data.role),
        full_name=data.full_name,
    )
    session.add(user)
    try:
        session.flush()
        if user.role == UserRole.CONTRIBUTOR:
            session.add(ContributorProfile(user_id=user.user_id))
        session.commit()
    except DBAPIError as exc:
        session.rollback()
        if duplicate_key(exc, "uq_user_account_email"):
            raise ConflictError(
                "An account with this email already exists", code="EMAIL_ALREADY_REGISTERED"
            ) from exc
        raise

    token, expires_in = create_access_token(user.user_id, user.role)
    return TokenResponse(
        access_token=token, expires_in=expires_in, user=UserRead.model_validate(user)
    )


def update_me(session: Session, user: UserAccount, full_name: str) -> UserAccount:
    """Change the caller's display name. Tokens don't carry the name, so they stay valid."""
    user.full_name = full_name
    session.commit()
    return user


def change_password(
    session: Session, user: UserAccount, current_password: str, new_password: str
) -> None:
    """Replace the caller's password after re-checking the current one.
    Tokens already issued stay valid until they expire."""
    if not verify_password(current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect", code="INVALID_CURRENT_PASSWORD")
    if same_password(new_password, current_password):
        raise UnprocessableError(
            "New password must differ from the current password", code="PASSWORD_UNCHANGED"
        )
    user.password_hash = hash_password(new_password)
    session.commit()
