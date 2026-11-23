"""main._on_opportunity_created: the creator's notification is stored through
DbNotifier as `opportunity_published` and committed before the handler returns (and
so before the message is acked). The database is faked."""

from datetime import UTC, datetime

import pytest
from grow8_common.events import EventEnvelope, EventType, OpportunityCreatedPayload
from grow8_common.models import NotificationType
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


def test_service_subscribes_to_its_events() -> None:
    assert list(main.HANDLERS) == [
        EventType.OPPORTUNITY_CREATED,
        EventType.APPLICATION_SUBMITTED,
        EventType.APPLICATION_WITHDRAWN,
        EventType.WORK_SUBMITTED,
        EventType.FEEDBACK_APPROVED,
        EventType.FEEDBACK_REJECTED,
        EventType.OPPORTUNITY_TAKEN_DOWN,
    ]


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
    notifier = seen["notifier"]
    assert isinstance(notifier, DbNotifier)
    assert notifier._event_id == str(envelope.event_id)
    assert notifier._type is NotificationType.OPPORTUNITY_PUBLISHED


def test_handler_error_commits_nothing(calls: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(payload, *, session, notifier):
        raise RuntimeError("database down")

    monkeypatch.setattr(main, "handle_opportunity_created", broken)

    with pytest.raises(RuntimeError):
        main._on_opportunity_created(_envelope(), PAYLOAD)
    assert calls == ["close"]  # process() then dead-letters the message


def test_application_submitted_uses_its_own_notification_type(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from grow8_common.events import ApplicationSubmittedPayload

    payload = ApplicationSubmittedPayload(
        application_id=41,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        contributor_name="Alex Chen",
    )
    seen = {}

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, "handle_application_submitted", fake_handler)

    main._on_application_submitted(
        EventEnvelope.build(payload, EventType.APPLICATION_SUBMITTED, "req-9"), payload
    )

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == NotificationType.APPLICATION_SUBMITTED


def test_application_withdrawn_uses_its_own_notification_type(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from grow8_common.events import ApplicationWithdrawnPayload

    payload = ApplicationWithdrawnPayload(
        application_id=41,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        contributor_name="Alex Chen",
        previous_status="accepted",
    )
    seen = {}

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, "handle_application_withdrawn", fake_handler)

    main._on_application_withdrawn(
        EventEnvelope.build(payload, EventType.APPLICATION_WITHDRAWN, "req-10"), payload
    )

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == NotificationType.APPLICATION_WITHDRAWN


def test_work_submitted_uses_its_own_notification_type(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from decimal import Decimal

    from grow8_common.events import WorkSubmittedPayload

    payload = WorkSubmittedPayload(
        submission_id=9,
        application_id=41,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        contributor_name="Alex Chen",
        hours_claimed=Decimal("6.50"),
        attachment_count=2,
    )
    seen = {}

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, "handle_work_submitted", fake_handler)

    main._on_work_submitted(
        EventEnvelope.build(payload, EventType.WORK_SUBMITTED, "req-11"), payload
    )

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == NotificationType.WORK_SUBMITTED
