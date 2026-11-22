from decimal import Decimal
from typing import Self

from grow8_common.models import Feedback, ReviewDecision
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import UtcDateTime
from app.services.feedback_rules import FeedbackStatus, feedback_status


def _blank_is_none(text: str | None) -> str | None:
    return text or None


class FeedbackCreate(BaseModel):
    """Feedback about the other participant on an application (ADR 0015)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rating: int = Field(ge=1, le=5, description="1 (poor) to 5 (excellent)")
    comment: str | None = Field(None, max_length=2_000, description="Optional")
    reports_discrepancy: bool = Field(
        False, description="Something on this application went wrong, e.g. disputed hours"
    )

    _comment = field_validator("comment")(_blank_is_none)


class ReviewCreate(BaseModel):
    """An admin's decision on feedback. Whether a rejection has a reason is a business
    rule checked by the service, so it gets its own error code."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: ReviewDecision
    reason: str | None = Field(
        None, max_length=500, description="Required when rejecting, optional when approving"
    )

    _reason = field_validator("reason")(_blank_is_none)


class Person(BaseModel):
    """Someone on the application. Contact details are not shared (ADR 0006)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str


class FeedbackOpportunity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: int
    title: str


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision: ReviewDecision
    reason: str | None
    reviewed_at: UtcDateTime


class FeedbackRead(BaseModel):
    feedback_id: int
    application_id: int
    opportunity: FeedbackOpportunity
    author: Person
    subject: Person
    rating: int
    comment: str | None
    reports_discrepancy: bool
    created_at: UtcDateTime
    status: FeedbackStatus = Field(description="pending until an admin reviews it")
    review: ReviewRead | None = Field(description="The admin's review, or null while pending")

    @classmethod
    def from_model(cls, feedback: Feedback) -> Self:
        review = feedback.review
        return cls(
            feedback_id=feedback.feedback_id,
            application_id=feedback.application_id,
            opportunity=FeedbackOpportunity.model_validate(feedback.application.opportunity),
            author=Person.model_validate(feedback.author),
            subject=Person.model_validate(feedback.subject),
            rating=feedback.rating,
            comment=feedback.comment,
            reports_discrepancy=feedback.reports_discrepancy,
            created_at=feedback.created_at,
            status=feedback_status(review.decision if review else None),
            review=ReviewRead.model_validate(review) if review else None,
        )


class ApplicationFeedback(BaseModel):
    """The feedback on an application that the caller may see."""

    given: FeedbackRead | None = Field(
        description="Your feedback about the other participant, in any status, or null"
    )
    received: FeedbackRead | None = Field(
        description="Their feedback about you, only once an admin approved it, or null"
    )


class AdminFeedbackParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: list[FeedbackStatus] = Field(
        default_factory=list, description="Status filter (repeatable); default all"
    )
    discrepancy: bool | None = Field(
        None, description="true: only discrepancy reports; false: only the others"
    )
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class UserRating(BaseModel):
    """Computed from approved feedback only (v_user_rating), never stored."""

    user_id: int
    average_rating: Decimal | None = Field(
        description="Average of approved ratings, 2 decimals; null with none"
    )
    approved_feedback_count: int
