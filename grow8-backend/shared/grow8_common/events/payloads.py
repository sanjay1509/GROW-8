from datetime import datetime
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


# Payload schema per event type. Add the others as their features are built.
PAYLOAD_SCHEMAS: dict[EventType, type[BaseModel]] = {
    EventType.OPPORTUNITY_CREATED: OpportunityCreatedPayload,
    EventType.OPPORTUNITY_CANCELLED: OpportunityCancelledPayload,
    EventType.APPLICATION_SUBMITTED: ApplicationSubmittedPayload,
    EventType.APPLICATION_DECIDED: ApplicationDecidedPayload,
    EventType.APPLICATION_WITHDRAWN: ApplicationWithdrawnPayload,
}
