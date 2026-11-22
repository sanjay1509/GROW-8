"""OPPORTUNITY_REPORTED, OPPORTUNITY_TAKEN_DOWN and REPORT_DISMISSED payloads (ADR 0016)."""

import pytest
from grow8_common.events import (
    PAYLOAD_SCHEMAS,
    EventEnvelope,
    EventType,
    OpportunityReportedPayload,
    OpportunityTakenDownPayload,
    ReportDismissedPayload,
)
from pydantic import ValidationError

PAYLOADS = [
    (
        EventType.OPPORTUNITY_REPORTED,
        "opportunity.reported",
        OpportunityReportedPayload(
            report_id=3,
            opportunity_id=1,
            opportunity_title="Recipes",
            reason="unsafe_conditions",
            open_reports=2,
        ),
    ),
    (
        EventType.OPPORTUNITY_TAKEN_DOWN,
        "opportunity.taken.down",
        OpportunityTakenDownPayload(
            opportunity_id=1,
            organization_id=1,
            title="Recipes",
            reason="Pay is misstated.",
            reporter_user_ids=[5, 6],
        ),
    ),
    (
        EventType.REPORT_DISMISSED,
        "report.dismissed",
        ReportDismissedPayload(
            report_id=3,
            opportunity_id=1,
            opportunity_title="Recipes",
            reporter_user_id=5,
            reason=None,
        ),
    ),
]


@pytest.mark.parametrize(("event_type", "routing_key", "payload"), PAYLOADS)
def test_each_has_a_payload_schema_and_round_trips(event_type, routing_key, payload) -> None:
    assert PAYLOAD_SCHEMAS[event_type] is type(payload)
    assert event_type.routing_key == routing_key

    envelope = EventEnvelope.build(payload, event_type, "req-1")
    wire = EventEnvelope.model_validate_json(envelope.model_dump_json())

    assert type(payload).model_validate(wire.payload) == payload


def test_the_report_reason_is_one_of_the_known_ones() -> None:
    with pytest.raises(ValidationError):
        OpportunityReportedPayload(
            report_id=3, opportunity_id=1, opportunity_title="x", reason="boring", open_reports=1
        )


def test_envelope_refuses_the_wrong_payload() -> None:
    _, _, dismissed = PAYLOADS[2]
    with pytest.raises(TypeError):
        EventEnvelope.build(dismissed, EventType.OPPORTUNITY_TAKEN_DOWN, None)
