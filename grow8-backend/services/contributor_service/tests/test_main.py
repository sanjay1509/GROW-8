"""main._on_opportunity_created: notifications are stored through DbNotifier for this
event and committed before the handler returns (and so before the message is acked).
The database is faked; DbNotifier itself is tested against MySQL in
api/tests/integration/test_db_notifier.py."""

from datetime import UTC, datetime

import pytest
from grow8_common.events import EventEnvelope, EventType, OpportunityCreatedPayload
from grow8_common.notifications import DbNotifier

from app import main

PAYLOAD = OpportunityCreatedPayload(
    opportunity_id=15,
    organization_id=3,
    title="Volunteer coordinator for spring market",
    category_code="community",
    application_deadline=datetime(2026, 11, 20, 23, 59, tzinfo=UTC),
    skill_codes=["customer-service", "event-setup"],
)


class FakeSession:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append("close")

    def commit(self) -> None:
        self.calls.append("commit")


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(main, "get_sessionmaker", lambda: lambda: FakeSession(calls))
    return calls


def _envelope() -> EventEnvelope:
    return EventEnvelope.build(PAYLOAD, EventType.OPPORTUNITY_CREATED, "req-123")


def test_handles_with_db_notifier_then_commits(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = {}

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, "handle_opportunity_created", fake_handler)
    envelope = _envelope()

    main._on_opportunity_created(envelope, PAYLOAD)

    assert calls == ["handle", "commit", "close"]
    assert isinstance(seen["notifier"], DbNotifier)
    assert seen["notifier"]._event_id == str(envelope.event_id)


def test_handler_error_commits_nothing(calls: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(payload, *, session, notifier):
        raise RuntimeError("database down")

    monkeypatch.setattr(main, "handle_opportunity_created", broken)

    with pytest.raises(RuntimeError):
        main._on_opportunity_created(_envelope(), PAYLOAD)
    assert calls == ["close"]  # process() then dead-letters the message


def test_application_decided_uses_its_own_notification_type(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from grow8_common.events import ApplicationDecidedPayload
    from grow8_common.models import NotificationType

    payload = ApplicationDecidedPayload(
        application_id=41,
        opportunity_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        decision="accepted",
    )
    seen = {}

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, "handle_application_decided", fake_handler)

    main._on_application_decided(
        EventEnvelope.build(payload, EventType.APPLICATION_DECIDED, "req-9"), payload
    )

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == NotificationType.APPLICATION_DECIDED


def test_subscribes_to_its_events() -> None:
    assert set(main.HANDLERS) == {
        EventType.OPPORTUNITY_CREATED,
        EventType.APPLICATION_DECIDED,
        EventType.OPPORTUNITY_CANCELLED,
        EventType.WORK_VERIFIED,
        EventType.WORK_REJECTED,
        EventType.FEEDBACK_APPROVED,
        EventType.FEEDBACK_REJECTED,
        EventType.OPPORTUNITY_TAKEN_DOWN,
        EventType.REPORT_DISMISSED,
    }


def test_opportunity_cancelled_uses_its_own_notification_type(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from grow8_common.events import OpportunityCancelledPayload
    from grow8_common.models import NotificationType

    payload = OpportunityCancelledPayload(opportunity_id=1, organization_id=1, title="Recipes")
    seen = {}

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, "handle_opportunity_cancelled", fake_handler)

    main._on_opportunity_cancelled(
        EventEnvelope.build(payload, EventType.OPPORTUNITY_CANCELLED, "req-11"), payload
    )

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == NotificationType.OPPORTUNITY_CANCELLED


@pytest.mark.parametrize(
    ("on_event", "handler_name", "event_type", "notification_type", "payload"),
    [
        (
            "_on_work_verified",
            "handle_work_verified",
            EventType.WORK_VERIFIED,
            "work_verified",
            {"verified_hours": "6.00"},
        ),
        (
            "_on_work_rejected",
            "handle_work_rejected",
            EventType.WORK_REJECTED,
            "work_rejected",
            {"comment": "Half is missing."},
        ),
    ],
)
def test_work_decisions_use_their_own_notification_type(
    calls: list[str],
    monkeypatch: pytest.MonkeyPatch,
    on_event: str,
    handler_name: str,
    event_type: EventType,
    notification_type: str,
    payload: dict,
) -> None:
    from grow8_common.events import PAYLOAD_SCHEMAS

    model = PAYLOAD_SCHEMAS[event_type].model_validate(
        {
            "verification_id": 7,
            "submission_id": 3,
            "application_id": 4,
            "opportunity_id": 1,
            "organization_id": 1,
            "opportunity_title": "Digitize paper recipe archive",
            "contributor_id": 5,
            **payload,
        }
    )
    seen = {}

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, handler_name, fake_handler)

    getattr(main, on_event)(EventEnvelope.build(model, event_type, "req-12"), model)

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == notification_type
