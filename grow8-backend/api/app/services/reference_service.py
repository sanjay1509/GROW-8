from collections.abc import Sequence

from grow8_common.models import OpportunityCategory, Skill
from sqlalchemy.orm import Session

from app.core.exceptions import UnprocessableError
from app.repositories import reference_repository


def list_categories(session: Session) -> Sequence[OpportunityCategory]:
    return reference_repository.list_categories(session)


def list_skills(session: Session) -> Sequence[Skill]:
    return reference_repository.list_skills(session)


def resolve_skills(session: Session, codes: Sequence[str]) -> list[Skill]:
    """The skills for these codes, in order, without duplicates. Used by opportunities and
    contributor profiles; any unknown code is a 422 UNKNOWN_SKILL listing all of them."""
    wanted = list(dict.fromkeys(codes))
    skills = reference_repository.get_skills_by_codes(session, wanted)
    found = {skill.code: skill for skill in skills}
    unknown = [code for code in wanted if code not in found]
    if unknown:
        raise UnprocessableError(
            "Unknown skill code(s)",
            code="UNKNOWN_SKILL",
            details={"unknown_skills": unknown},
        )
    return [found[code] for code in wanted]
