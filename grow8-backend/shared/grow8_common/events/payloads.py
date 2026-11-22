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
}
