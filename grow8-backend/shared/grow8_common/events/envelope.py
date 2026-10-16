from datetime import UTC, datetime
from typing import Any, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from grow8_common.events.payloads import PAYLOAD_SCHEMAS
from grow8_common.events.types import EventType


class EventEnvelope(BaseModel):
    """Wrapper shared by every event on the bus (see CLAUDE.md section 7)."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    version: int = 1
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    payload: dict[str, Any]

    @classmethod
    def build(cls, payload: BaseModel, event_type: EventType, correlation_id: str | None) -> Self:
        expected = PAYLOAD_SCHEMAS.get(event_type)
        if expected is None or not isinstance(payload, expected):
            raise TypeError(f"{type(payload).__name__} is not the payload schema for {event_type}")
        return cls(
            event_type=event_type,
            correlation_id=correlation_id,
            payload=payload.model_dump(mode="json"),
        )

    @property
    def routing_key(self) -> str:
        return self.event_type.routing_key
