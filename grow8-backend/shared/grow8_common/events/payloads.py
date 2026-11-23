from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from grow8_common.events.types import EventType


class OpportunityCreatedPayload(BaseModel):
    """Sent when an opportunity is published and becomes visible to contributors."""

    opportunity_id: int
    organization_id: int
    title: str
    category_code: str
    application_deadline: datetime
    skill_codes: list[str]


class OpportunityCancelledPayload(BaseModel):
    """Sent when the owning creator cancels an open or closed opportunity. Who to tell
    (pending and accepted applicants) is looked up when the event is handled."""

    opportunity_id: int
    organization_id: int
    title: str


class ApplicationSubmittedPayload(BaseModel):
    """Sent when a contributor applies to an open opportunity."""

    application_id: int
    opportunity_id: int
    organization_id: int
    opportunity_title: str
    contributor_id: int
    contributor_name: str


class ApplicationDecidedPayload(BaseModel):
    """Sent when the owning creator accepts or rejects a pending application."""

    application_id: int
    opportunity_id: int
    opportunity_title: str
    contributor_id: int
    decision: Literal["accepted", "rejected"]


class ApplicationWithdrawnPayload(BaseModel):
    """Sent when a contributor withdraws a pending or accepted application."""

    application_id: int
    opportunity_id: int
    organization_id: int
    opportunity_title: str
    contributor_id: int
    contributor_name: str
    previous_status: Literal["pending", "accepted"]


class WorkSubmittedPayload(BaseModel):
    """Sent when an accepted applicant submits their work for verification (ADR 0012).
    `hours_claimed` travels as a JSON string (e.g. "6.50") so no precision is lost."""

    submission_id: int
    application_id: int
    opportunity_id: int
    organization_id: int
    opportunity_title: str
    contributor_id: int
    contributor_name: str
    hours_claimed: Decimal
    attachment_count: int


class WorkVerifiedPayload(BaseModel):
    """Sent when the owning creator approves submitted work (ADR 0013). Each submission
    is verified once, so `verification_id` identifies this approval for good (the rewards
    handler awards its points once per verification). `verified_hours` travels as a
    JSON string (e.g. "6.00") so no precision is lost."""

    verification_id: int
    submission_id: int
    application_id: int
    opportunity_id: int
    organization_id: int
    opportunity_title: str
    contributor_id: int
    verified_hours: Decimal


class WorkRejectedPayload(BaseModel):
    """Sent when the owning creator rejects submitted work (ADR 0013), with the comment
    that says why (required when rejecting)."""

    verification_id: int
    submission_id: int
    application_id: int
    opportunity_id: int
    organization_id: int
    opportunity_title: str
    contributor_id: int
    comment: str


# Which participant wrote the feedback. The decision events go to creator_service and
# contributor_service, and each one notifies only the participant on its own side.
AuthorRole = Literal["contributor", "creator"]


class FeedbackSubmittedPayload(BaseModel):
    """Sent when a participant leaves feedback on a verified application (ADR 0015). It
    waits for an admin's review."""

    feedback_id: int
    application_id: int
    opportunity_id: int
    opportunity_title: str
    author_user_id: int
    author_name: str
    author_role: AuthorRole
    subject_user_id: int
    rating: int
    reports_discrepancy: bool


class FeedbackApprovedPayload(BaseModel):
    """Sent when an admin approves feedback: it is now public and counts toward the
    subject's rating. Both the author and the subject are told (ADR 0015)."""

    feedback_id: int
    application_id: int
    opportunity_id: int
    opportunity_title: str
    author_user_id: int
    author_name: str
    author_role: AuthorRole
    subject_user_id: int
    subject_name: str
    rating: int


class FeedbackRejectedPayload(BaseModel):
    """Sent when an admin rejects feedback, with the reason (required). Only the author
    is told; the subject never sees feedback that doesn't count (ADR 0015)."""

    feedback_id: int
    application_id: int
    opportunity_id: int
    opportunity_title: str
    author_user_id: int
    author_role: AuthorRole
    subject_name: str
    reason: str


class OpportunityReportedPayload(BaseModel):
    """Sent when a contributor reports a published opportunity (ADR 0016). The reporter
    is not named: admins see who reported through the API."""

    report_id: int
    opportunity_id: int
    opportunity_title: str
    reason: Literal[
        "misleading_terms", "unsafe_conditions", "discriminatory", "scam_or_spam", "other"
    ]
    open_reports: int  # pending reports on this opportunity, this one included


class OpportunityTakenDownPayload(BaseModel):
    """Sent when an admin upholds a report and the opportunity is cancelled (ADR 0016).
    `reason` is what the admin told the creator. Applicants are looked up when the event
    is handled; the reporters are listed here, since every pending report was upheld."""

    opportunity_id: int
    organization_id: int
    title: str
    reason: str
    reporter_user_ids: list[int]


class ReportDismissedPayload(BaseModel):
    """Sent when an admin dismisses one report; only its reporter is told."""

    report_id: int
    opportunity_id: int
    opportunity_title: str
    reporter_user_id: int
    reason: str | None


# Payload schema per event type. Add the others as their features are built.
PAYLOAD_SCHEMAS: dict[EventType, type[BaseModel]] = {
    EventType.OPPORTUNITY_CREATED: OpportunityCreatedPayload,
    EventType.OPPORTUNITY_CANCELLED: OpportunityCancelledPayload,
    EventType.APPLICATION_SUBMITTED: ApplicationSubmittedPayload,
    EventType.APPLICATION_DECIDED: ApplicationDecidedPayload,
    EventType.APPLICATION_WITHDRAWN: ApplicationWithdrawnPayload,
    EventType.WORK_SUBMITTED: WorkSubmittedPayload,
    EventType.WORK_VERIFIED: WorkVerifiedPayload,
    EventType.WORK_REJECTED: WorkRejectedPayload,
    EventType.FEEDBACK_SUBMITTED: FeedbackSubmittedPayload,
    EventType.FEEDBACK_APPROVED: FeedbackApprovedPayload,
    EventType.FEEDBACK_REJECTED: FeedbackRejectedPayload,
    EventType.OPPORTUNITY_REPORTED: OpportunityReportedPayload,
    EventType.OPPORTUNITY_TAKEN_DOWN: OpportunityTakenDownPayload,
    EventType.REPORT_DISMISSED: ReportDismissedPayload,
}
