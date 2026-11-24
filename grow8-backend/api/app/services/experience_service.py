"""The signed-in contributor's verified experience (GET /contributors/me/experience).

Read-only. Totals come from v_contributor_verified_hours and skills from
v_contributor_skill, so this page, badges and the leaderboard agree by construction."""

from decimal import Decimal

from grow8_common.models import UserAccount
from sqlalchemy.orm import Session

from app.repositories import experience_repository, user_repository
from app.schemas.experience import (
    CompletedWork,
    ExperienceOpportunity,
    ExperienceOrganization,
    ExperienceRead,
    VerifiedSkill,
)

_CENTS = Decimal("0.01")


def get_mine(session: Session, contributor: UserAccount) -> ExperienceRead:
    totals = experience_repository.totals(session, contributor.user_id)
    work = experience_repository.completed_work(session, contributor.user_id)
    skills = [
        skill
        for skill in user_repository.skills_of(session, contributor.user_id)
        if skill.is_verified
    ]
    return ExperienceRead(
        verified_hours=totals.verified_hours.quantize(_CENTS),
        completed_opportunities=totals.completed_opportunities,
        organizations=len({row.organization_id for row in work}),
        verified_skills=[
            VerifiedSkill(code=skill.code, name=skill.name, verified_at=skill.verified_at)
            for skill in skills
        ],
        completed_work=[
            CompletedWork(
                application_id=row.application_id,
                submission_id=row.submission_id,
                opportunity=ExperienceOpportunity(
                    opportunity_id=row.opportunity_id, title=row.opportunity_title
                ),
                organization=ExperienceOrganization(
                    organization_id=row.organization_id, name=row.organization_name
                ),
                description=row.description,
                verified_hours=row.verified_hours.quantize(_CENTS),
                comment=row.comment,
                verified_at=row.verified_at,
            )
            for row in work
        ],
    )
