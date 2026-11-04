from datetime import datetime

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


# Payload schema per event type. Add the others as their features are built.
PAYLOAD_SCHEMAS: dict[EventType, type[BaseModel]] = {
    EventType.OPPORTUNITY_CREATED: OpportunityCreatedPayload,
}
