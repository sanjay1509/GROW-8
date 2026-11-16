from grow8_common.models import ContributorProfile, ContributorResume
from sqlalchemy import select
from sqlalchemy.orm import Session


def get(session: Session, user_id: int) -> ContributorResume | None:
    return session.get(ContributorResume, user_id)


def lock_profile(session: Session, user_id: int) -> ContributorProfile | None:
    """Row-lock the contributor's profile until the transaction ends, so two uploads
    by the same contributor run one after the other."""
    stmt = select(ContributorProfile).where(ContributorProfile.user_id == user_id)
    return session.scalars(stmt.with_for_update()).first()


def add(session: Session, resume: ContributorResume) -> None:
    session.add(resume)


def delete(session: Session, resume: ContributorResume) -> None:
    session.delete(resume)
