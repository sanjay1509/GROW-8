"""WORK_VERIFIED and WORK_REJECTED payloads (ADR 0013): registered for their event types,
and verified hours keep their precision on the wire."""

from decimal import Decimal

import pytest
from grow8_common.events import (
    PAYLOAD_SCHEMAS,
    EventEnvelope,
    EventType,
    WorkRejectedPayload,
    WorkVerifiedPayload,
)


def _verified(hours: str = "6.00") -> WorkVerifiedPayload:
    return WorkVerifiedPayload(
        verification_id=7,
        submission_id=3,
        application_id=4,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        verified_hours=Decimal(hours),
    )


def _rejected() -> WorkRejectedPayload:
    return WorkRejectedPayload(
        verification_id=8,
        submission_id=3,
        application_id=4,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        comment="The sheet is missing half the recipes.",
    )


@pytest.mark.parametrize(
    ("event_type", "schema", "routing_key"),
    [
        (EventType.WORK_VERIFIED, WorkVerifiedPayload, "work.verified"),
        (EventType.WORK_REJECTED, WorkRejectedPayload, "work.rejected"),
    ],
)
def test_each_has_a_payload_schema(event_type: EventType, schema: type, routing_key: str) -> None:
    assert PAYLOAD_SCHEMAS[event_type] is schema
    assert event_type.routing_key == routing_key


def test_verified_hours_keep_their_precision_through_the_envelope() -> None:
    envelope = EventEnvelope.build(_verified("5.50"), EventType.WORK_VERIFIED, "req-1")

    wire = EventEnvelope.model_validate_json(envelope.model_dump_json())
    received = WorkVerifiedPayload.model_validate(wire.payload)

    assert envelope.payload["verified_hours"] == "5.50"
    assert received == _verified("5.50")


def test_rejected_round_trips_with_its_comment() -> None:
    envelope = EventEnvelope.build(_rejected(), EventType.WORK_REJECTED, "req-2")

    wire = EventEnvelope.model_validate_json(envelope.model_dump_json())

    assert WorkRejectedPayload.model_validate(wire.payload) == _rejected()


def test_envelope_refuses_the_wrong_payload() -> None:
    with pytest.raises(TypeError):
        EventEnvelope.build(_rejected(), EventType.WORK_VERIFIED, None)
    with pytest.raises(TypeError):
        EventEnvelope.build(_verified(), EventType.WORK_REJECTED, None)
