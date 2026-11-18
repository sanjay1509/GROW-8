from decimal import Decimal

import pytest
from grow8_common.events import (
    PAYLOAD_SCHEMAS,
    ApplicationSubmittedPayload,
    EventEnvelope,
    EventType,
    WorkSubmittedPayload,
)


def _payload(hours: str = "6.50") -> WorkSubmittedPayload:
    return WorkSubmittedPayload(
        submission_id=1,
        application_id=4,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        contributor_name="Alex Chen",
        hours_claimed=Decimal(hours),
        attachment_count=2,
    )


def test_work_submitted_has_a_payload_schema() -> None:
    assert PAYLOAD_SCHEMAS[EventType.WORK_SUBMITTED] is WorkSubmittedPayload
    assert EventType.WORK_SUBMITTED.routing_key == "work.submitted"


def test_hours_claimed_keeps_its_precision_through_the_envelope() -> None:
    envelope = EventEnvelope.build(_payload("6.50"), EventType.WORK_SUBMITTED, "req-1")

    wire = EventEnvelope.model_validate_json(envelope.model_dump_json())
    received = WorkSubmittedPayload.model_validate(wire.payload)

    assert envelope.payload["hours_claimed"] == "6.50"
    assert received.hours_claimed == Decimal("6.50")
    assert received == _payload("6.50")


def test_envelope_refuses_the_wrong_payload_for_work_submitted() -> None:
    wrong = ApplicationSubmittedPayload(
        application_id=4,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        contributor_name="Alex Chen",
    )
    with pytest.raises(TypeError):
        EventEnvelope.build(wrong, EventType.WORK_SUBMITTED, None)
