"""grow8_common.messaging.process(): when a message is acknowledged and when it is
dead-lettered. No RabbitMQ needed; process() does no I/O of its own."""

import json
from datetime import UTC, datetime

from grow8_common.events import EventEnvelope, EventType, OpportunityCreatedPayload
from grow8_common.messaging import Outcome, process

from app import main

PAYLOAD = OpportunityCreatedPayload(
    opportunity_id=1,
    organization_id=1,
    title="Digitize paper invoices",
    category_code="knowledge",
    application_deadline=datetime(2026, 11, 1, tzinfo=UTC),
    skill_codes=["data-entry"],
)


def _body(event_type: EventType = EventType.OPPORTUNITY_CREATED, **payload_overrides) -> bytes:
    envelope = EventEnvelope.build(PAYLOAD, EventType.OPPORTUNITY_CREATED, "req-123")
    data = json.loads(envelope.model_dump_json())
    data["event_type"] = event_type.value
    data["payload"].update(payload_overrides)
    return json.dumps(data).encode()


def test_valid_event_runs_handler_and_is_acked() -> None:
    received = []
    handlers = {EventType.OPPORTUNITY_CREATED: lambda env, payload: received.append((env, payload))}

    assert process(_body(), handlers) is Outcome.ACK
    envelope, payload = received[0]
    assert envelope.correlation_id == "req-123"
    assert isinstance(payload, OpportunityCreatedPayload)
    assert payload.skill_codes == ["data-entry"]


def test_unreadable_message_is_dead_lettered() -> None:
    assert process(b"not json", {}) is Outcome.DEAD_LETTER


def test_event_without_handler_is_dead_lettered() -> None:
    handlers = {EventType.OPPORTUNITY_CREATED: lambda env, payload: None}
    assert process(_body(EventType.WORK_VERIFIED), handlers) is Outcome.DEAD_LETTER


def test_invalid_payload_is_dead_lettered_without_calling_handler() -> None:
    called = []
    handlers = {EventType.OPPORTUNITY_CREATED: lambda env, payload: called.append(payload)}
    assert process(_body(opportunity_id="not-a-number"), handlers) is Outcome.DEAD_LETTER
    assert called == []


def test_handler_error_is_dead_lettered() -> None:
    def broken(env, payload):
        raise RuntimeError("database down")

    assert process(_body(), {EventType.OPPORTUNITY_CREATED: broken}) is Outcome.DEAD_LETTER


def test_service_subscribes_to_opportunity_created() -> None:
    assert EventType.OPPORTUNITY_CREATED in main.HANDLERS
    assert EventType.OPPORTUNITY_CREATED.routing_key == "opportunity.created"
