"""FEEDBACK_SUBMITTED, FEEDBACK_APPROVED and FEEDBACK_REJECTED payloads (ADR 0015)."""

import pytest
from grow8_common.events import (
    PAYLOAD_SCHEMAS,
    EventEnvelope,
    EventType,
    FeedbackApprovedPayload,
    FeedbackRejectedPayload,
    FeedbackSubmittedPayload,
)
from pydantic import BaseModel, ValidationError

COMMON = {
    "feedback_id": 9,
    "application_id": 4,
    "opportunity_id": 1,
    "opportunity_title": "Digitize paper recipe archive",
    "author_user_id": 5,
    "author_role": "contributor",
}

PAYLOADS: list[tuple[EventType, BaseModel]] = [
    (
        EventType.FEEDBACK_SUBMITTED,
        FeedbackSubmittedPayload(
            **COMMON,
            author_name="Alex Chen",
            subject_user_id=2,
            rating=4,
            reports_discrepancy=True,
        ),
    ),
    (
        EventType.FEEDBACK_APPROVED,
        FeedbackApprovedPayload(
            **COMMON,
            author_name="Alex Chen",
            subject_user_id=2,
            subject_name="Priya Nair",
            rating=4,
        ),
    ),
    (
        EventType.FEEDBACK_REJECTED,
        FeedbackRejectedPayload(**COMMON, subject_name="Priya Nair", reason="Personal remarks."),
    ),
]


@pytest.mark.parametrize(("event_type", "payload"), PAYLOADS)
def test_each_has_a_payload_schema_and_round_trips(event_type, payload) -> None:
    assert PAYLOAD_SCHEMAS[event_type] is type(payload)
    assert event_type.routing_key == event_type.value.lower().replace("_", ".")

    envelope = EventEnvelope.build(payload, event_type, "req-1")
    wire = EventEnvelope.model_validate_json(envelope.model_dump_json())

    assert type(payload).model_validate(wire.payload) == payload


def test_the_author_role_is_contributor_or_creator() -> None:
    with pytest.raises(ValidationError):
        FeedbackRejectedPayload(**{**COMMON, "author_role": "admin"}, subject_name="x", reason="y")


def test_envelope_refuses_the_wrong_payload() -> None:
    _, rejected = PAYLOADS[2]
    with pytest.raises(TypeError):
        EventEnvelope.build(rejected, EventType.FEEDBACK_APPROVED, None)
