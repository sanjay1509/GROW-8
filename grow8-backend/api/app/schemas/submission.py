from decimal import Decimal
from typing import Annotated, Self

from grow8_common.models import OpportunityStatus, ReviewDecision, WorkSubmission
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import UtcDateTime
from app.services.verification_rules import SubmissionStatus, submission_status

_CENTS = Decimal("0.01")
_MAX_HOURS = Decimal("9999.99")

# Hours always carry two decimals, as in the DECIMAL(6, 2) column, so a submission reads
# the same ("6.50") whether it was just created or loaded again later.
Hours = Annotated[Decimal, AfterValidator(lambda hours: hours.quantize(_CENTS))]
# For an optional field the constraints must sit on the inner type: on `Hours | None`,
# decimal_places would only be checked after the rounding above, so 1.234 would pass.
PositiveHours = Annotated[
    Decimal,
    Field(gt=0, le=_MAX_HOURS, decimal_places=2),
    AfterValidator(lambda hours: hours.quantize(_CENTS)),
]


class SubmissionCreate(BaseModel):
    """The form fields of a work submission; the files travel next to them."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=5_000, description="What you did")
    hours_claimed: Hours = Field(
        gt=0, le=_MAX_HOURS, decimal_places=2, description="Hours you worked"
    )


class VerificationCreate(BaseModel):
    """The creator's decision on submitted work (ADR 0013). Whether the hours fit the
    claim and whether a rejection has a comment are business rules checked by the
    service, so they get their own error codes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: ReviewDecision
    verified_hours: PositiveHours | None = Field(
        None,
        description="Required when approving: at most the hours claimed. Leave out when rejecting",
    )
    comment: str | None = Field(
        None, max_length=2_000, description="Required when rejecting, optional when approving"
    )

    @field_validator("comment")
    @classmethod
    def _blank_is_none(cls, comment: str | None) -> str | None:
        return comment or None

    @model_validator(mode="after")
    def _hours_match_decision(self) -> Self:
        if self.decision == ReviewDecision.APPROVED and self.verified_hours is None:
            raise ValueError("verified_hours is required when approving")
        if self.decision == ReviewDecision.REJECTED and self.verified_hours is not None:
            raise ValueError("verified_hours must be left out when rejecting")
        return self


class AttachmentRead(BaseModel):
    """An attachment's metadata. The file itself is downloaded separately."""

    model_config = ConfigDict(from_attributes=True)

    attachment_id: int
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_at: UtcDateTime


class VerificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision: ReviewDecision
    verified_hours: Hours | None
    comment: str | None
    verified_at: UtcDateTime


class SubmissionOpportunity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: int
    title: str
    status: OpportunityStatus


class SubmissionApplicant(BaseModel):
    """Who submitted the work. Contact details are not shared (ADR 0006)."""

    user_id: int
    full_name: str


class SubmissionRead(BaseModel):
    submission_id: int
    application_id: int
    status: SubmissionStatus = Field(description="awaiting until the creator decides")
    description: str
    hours_claimed: Hours
    submitted_at: UtcDateTime
    opportunity: SubmissionOpportunity
    applicant: SubmissionApplicant
    attachments: list[AttachmentRead]
    verification: VerificationRead | None = Field(
        description="The creator's decision, or null while awaiting verification"
    )

    @classmethod
    def from_model(cls, submission: WorkSubmission) -> Self:
        application = submission.application
        verification = submission.verification
        return cls(
            submission_id=submission.submission_id,
            application_id=submission.application_id,
            status=submission_status(verification.decision if verification else None),
            description=submission.description,
            hours_claimed=submission.hours_claimed,
            submitted_at=submission.submitted_at,
            opportunity=SubmissionOpportunity.model_validate(application.opportunity),
            applicant=SubmissionApplicant(
                user_id=application.contributor_id,
                full_name=application.contributor.user.full_name,
            ),
            attachments=[AttachmentRead.model_validate(a) for a in submission.attachments],
            verification=VerificationRead.model_validate(verification) if verification else None,
        )


class ReceivedSubmissionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: list[SubmissionStatus] = Field(
        default_factory=list, description="Status filter (repeatable); default all"
    )
    opportunity_id: int | None = Field(
        None, ge=1, description="Only this one of your opportunities (default: all of them)"
    )
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
