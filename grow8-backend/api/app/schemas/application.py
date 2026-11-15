from enum import StrEnum
from typing import Self

from grow8_common.models import Application, ApplicationStatus, OpportunityStatus
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime
from app.schemas.opportunity import OrganizationSummary
from app.schemas.reference import SkillRead


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    motivation: str | None = Field(
        None, min_length=1, max_length=5_000, description="Why you are a good fit (optional)"
    )


class Decision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ApplicationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision


class ApplicationOpportunity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: int
    title: str
    status: OpportunityStatus
    application_deadline: UtcDateTime | None
    organization: OrganizationSummary


class Applicant(BaseModel):
    """The contributor's public profile. Contact details are not shared."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str
    headline: str | None
    institution: str | None
    city: str | None
    skills: list[SkillRead]


class ApplicationRead(BaseModel):
    application_id: int
    status: ApplicationStatus
    motivation: str | None
    submitted_at: UtcDateTime
    decided_at: UtcDateTime | None
    opportunity: ApplicationOpportunity
    applicant: Applicant

    @classmethod
    def from_model(cls, application: Application) -> Self:
        profile = application.contributor
        return cls(
            application_id=application.application_id,
            status=application.status,
            motivation=application.motivation,
            submitted_at=application.submitted_at,
            decided_at=application.decided_at,
            opportunity=ApplicationOpportunity.model_validate(application.opportunity),
            applicant=Applicant(
                user_id=profile.user_id,
                full_name=profile.user.full_name,
                headline=profile.headline,
                institution=profile.institution,
                city=profile.city,
                skills=[SkillRead.model_validate(s) for s in profile.skills],
            ),
        )


class ApplicationListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: list[ApplicationStatus] = Field(
        default_factory=list, description="Status filter (repeatable); default all"
    )
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
