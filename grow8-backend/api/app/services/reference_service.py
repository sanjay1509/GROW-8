from collections.abc import Sequence

from grow8_common.models import OpportunityCategory, Skill
from sqlalchemy.orm import Session

from app.repositories import reference_repository


def list_categories(session: Session) -> Sequence[OpportunityCategory]:
    return reference_repository.list_categories(session)


def list_skills(session: Session) -> Sequence[Skill]:
    return reference_repository.list_skills(session)
