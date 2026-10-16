from grow8_common.models import CreatorOrganization, UserAccount
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_by_id(session: Session, user_id: int) -> UserAccount | None:
    return session.get(UserAccount, user_id)


def get_by_email(session: Session, email: str) -> UserAccount | None:
    return session.scalars(select(UserAccount).where(UserAccount.email == email)).first()


def get_organization_of(session: Session, owner_user_id: int) -> CreatorOrganization | None:
    stmt = select(CreatorOrganization).where(CreatorOrganization.owner_user_id == owner_user_id)
    return session.scalars(stmt).first()
