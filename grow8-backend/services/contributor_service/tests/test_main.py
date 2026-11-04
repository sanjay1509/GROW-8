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
