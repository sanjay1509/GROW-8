from grow8_common.events import EventEnvelope, EventType
from pydantic import BaseModel


class FakePublisher:
    """Records events instead of sending them to RabbitMQ."""

    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    def publish(
        self, payload: BaseModel, event_type: EventType, correlation_id: str | None
    ) -> None:
        self.events.append(EventEnvelope.build(payload, event_type, correlation_id))
