from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from grow8_common.models import (
    ContributorProfile,
    ContributorSkill,
    CreatorOrganization,
    UserAccount,
)
from sqlalchemy import delete, select, text
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session


def get_by_id(session: Session, user_id: int) -> UserAccount | None:
    return session.get(UserAccount, user_id)


def get_by_email(session: Session, email: str) -> UserAccount | None:
    return session.scalars(select(UserAccount).where(UserAccount.email == email)).first()


def get_organization_of(session: Session, owner_user_id: int) -> CreatorOrganization | None:
    stmt = select(CreatorOrganization).where(CreatorOrganization.owner_user_id == owner_user_id)
    return session.scalars(stmt).first()


def lock_organization_of(session: Session, owner_user_id: int) -> CreatorOrganization | None:
    """Row-lock the creator's account, then return their organization (locked too), or
    None. Locking the account first means two saves by the same creator run one after the
    other even when there is no organization row yet to lock (ADR 0018)."""
    session.execute(
        select(UserAccount.user_id).where(UserAccount.user_id == owner_user_id).with_for_update()
    )
    stmt = select(CreatorOrganization).where(CreatorOrganization.owner_user_id == owner_user_id)
    return session.scalars(stmt.with_for_update().execution_options(populate_existing=True)).first()


def add_organization(session: Session, organization: CreatorOrganization) -> None:
    session.add(organization)


def get_contributor_profile(session: Session, user_id: int) -> ContributorProfile | None:
    return session.get(ContributorProfile, user_id)


def lock_contributor_profile(session: Session, user_id: int) -> ContributorProfile:
    """Create the contributor's profile row if it is missing, then row-lock it until the
    transaction ends (ADR 0017). Locking a row that doesn't exist locks nothing, so the
    row is ensured first, with a no-op ON DUPLICATE KEY UPDATE (never INSERT IGNORE,
    which would hide other errors, ADR 0010)."""
    ensure = insert(ContributorProfile).values(user_id=user_id)
    session.execute(ensure.on_duplicate_key_update(user_id=ensure.inserted.user_id))
    stmt = select(ContributorProfile).where(ContributorProfile.user_id == user_id)
    return session.scalars(stmt.with_for_update().execution_options(populate_existing=True)).one()


@dataclass(frozen=True)
class ContributorSkillRow:
    skill_id: int
    code: str
    name: str
    is_listed: bool
    is_verified: bool
    verified_at: datetime | None


def skills_of(session: Session, user_id: int) -> list[ContributorSkillRow]:
    """Every skill the contributor listed or earned through approved work, sorted by name.
    Read from v_contributor_skill, so there is one definition of listed and verified
    (decision 7, ADR 0019)."""
    rows = session.execute(
        text(
            "SELECT s.skill_id, s.code, s.name, v.is_listed, v.is_verified, v.verified_at "
            "FROM v_contributor_skill v JOIN skill s ON s.skill_id = v.skill_id "
            "WHERE v.contributor_id = :user_id ORDER BY s.name"
        ),
        {"user_id": user_id},
    ).all()
    return [
        ContributorSkillRow(
            r.skill_id, r.code, r.name, bool(r.is_listed), bool(r.is_verified), r.verified_at
        )
        for r in rows
    ]


def listed_skill_ids(session: Session, user_id: int) -> set[int]:
    stmt = select(ContributorSkill.skill_id).where(ContributorSkill.contributor_id == user_id)
    return set(session.scalars(stmt))


def remove_skills(session: Session, user_id: int, skill_ids: Sequence[int]) -> None:
    if skill_ids:
        session.execute(
            delete(ContributorSkill).where(
                ContributorSkill.contributor_id == user_id,
                ContributorSkill.skill_id.in_(skill_ids),
            )
        )


def add_skills(session: Session, user_id: int, skill_ids: Sequence[int]) -> None:
    session.add_all(ContributorSkill(contributor_id=user_id, skill_id=s) for s in skill_ids)
