from enum import StrEnum
from typing import Annotated, Self

from grow8_common.models import Application, ApplicationStatus, OpportunityStatus
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime
from app.schemas.opportunity import OrganizationSummary
from app.schemas.reference import SkillRead
from app.services.verification_rules import WorkStatus, work_status

MAX_DETAILS = 20
DetailKey = Annotated[str, Field(min_length=1, max_length=50)]
DetailValue = Annotated[str, Field(max_length=2_000)]


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    motivation: str | None = Field(
        None, min_length=1, max_length=5_000, description="Why you are a good fit (optional)"
    )
    application_details: dict[DetailKey, DetailValue] = Field(
        default_factory=dict,
        max_length=MAX_DETAILS,
        description=f"Extra answers from the apply form: at most {MAX_DETAILS} entries, "
        "keys of 1-50 characters, values of at most 2000",
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
    has_resume: bool = False  # download via GET /applications/{id}/resume


class ApplicationRead(BaseModel):
    application_id: int
    status: ApplicationStatus
    motivation: str | None
    application_details: dict[str, str] = Field(default_factory=dict)
    submitted_at: UtcDateTime
    decided_at: UtcDateTime | None
    opportunity: ApplicationOpportunity
    applicant: Applicant
    submission_id: int | None = Field(
        description="The submitted work's id, or null if no work has been submitted yet"
    )
    work_status: WorkStatus = Field(
        description="not_submitted, awaiting_verification, completed (approved) or work_rejected"
    )

    @classmethod
    def from_model(cls, application: Application) -> Self:
        profile = application.contributor
        submission = application.submission
        return cls(
            application_id=application.application_id,
            status=application.status,
            motivation=application.motivation,
            application_details=application.application_details or {},
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
                has_resume=(
                    application.resume_storage_key is not None or profile.resume is not None
                ),
            ),
            submission_id=submission.submission_id if submission else None,
            work_status=work_status(
                submission is not None,
                submission.verification.decision
                if submission and submission.verification
                else None,
            ),
        )


class ApplicationListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: list[ApplicationStatus] = Field(
        default_factory=list, description="Status filter (repeatable); default all"
    )
    opportunity_id: int | None = Field(
        None, ge=1, description="Only applications for this opportunity"
    )
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class ReceivedApplicationParams(ApplicationListParams):
    pass
