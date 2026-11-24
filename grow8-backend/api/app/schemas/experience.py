from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import UtcDateTime


class ExperienceOpportunity(BaseModel):
    opportunity_id: int
    title: str


class ExperienceOrganization(BaseModel):
    organization_id: int
    name: str


class CompletedWork(BaseModel):
    """One piece of work an organization approved."""

    application_id: int
    submission_id: int
    opportunity: ExperienceOpportunity
    organization: ExperienceOrganization
    description: str
    verified_hours: Decimal
    comment: str | None
    verified_at: UtcDateTime


class VerifiedSkill(BaseModel):
    code: str
    name: str
    verified_at: UtcDateTime | None


class ExperienceRead(BaseModel):
    """The contributor's verified record (SDG 8.6): approved hours, the work behind them
    and the skills that work proved."""

    verified_hours: Decimal
    completed_opportunities: int
    organizations: int
    verified_skills: list[VerifiedSkill]
    completed_work: list[CompletedWork]
