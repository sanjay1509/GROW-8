from collections.abc import Sequence

from grow8_common.models import OpportunityCategory, Skill
from sqlalchemy import select
from sqlalchemy.orm import Session


def list_categories(session: Session) -> Sequence[OpportunityCategory]:
    return session.scalars(select(OpportunityCategory).order_by(OpportunityCategory.name)).all()


def list_skills(session: Session) -> Sequence[Skill]:
    return session.scalars(select(Skill).order_by(Skill.name)).all()


def get_category_by_code(session: Session, code: str) -> OpportunityCategory | None:
    stmt = select(OpportunityCategory).where(OpportunityCategory.code == code)
    return session.scalars(stmt).first()


def get_skills_by_codes(session: Session, codes: Sequence[str]) -> Sequence[Skill]:
    if not codes:
        return []
    return session.scalars(select(Skill).where(Skill.code.in_(codes))).all()
