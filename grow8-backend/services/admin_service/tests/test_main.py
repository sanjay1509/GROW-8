"""main._on_feedback_submitted: notifications go through DbNotifier for this event and
are committed before the handler returns (so before the message is acked)."""

import pytest
from grow8_common.events import EventEnvelope, EventType, FeedbackSubmittedPayload
from grow8_common.models import NotificationType
from grow8_common.notifications import DbNotifier

from app import main

PAYLOAD = FeedbackSubmittedPayload(
    feedback_id=9,
    application_id=4,
    opportunity_id=1,
    opportunity_title="Digitize paper recipe archive",
    author_user_id=5,
    author_name="Alex Chen",
    author_role="contributor",
    subject_user_id=2,
    rating=4,
    reports_discrepancy=False,
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


def test_subscribes_to_its_events() -> None:
    assert set(main.HANDLERS) == {EventType.FEEDBACK_SUBMITTED, EventType.OPPORTUNITY_REPORTED}


def test_handles_with_db_notifier_then_commits(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = {}

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, "handle_feedback_submitted", fake_handler)
    envelope = EventEnvelope.build(PAYLOAD, EventType.FEEDBACK_SUBMITTED, "req-1")

    main._on_feedback_submitted(envelope, PAYLOAD)

    assert calls == ["handle", "commit", "close"]
    assert isinstance(seen["notifier"], DbNotifier)
    assert seen["notifier"]._type == NotificationType.FEEDBACK_SUBMITTED
    assert seen["notifier"]._event_id == str(envelope.event_id)


def test_handler_error_commits_nothing(calls: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(payload, *, session, notifier):
        raise RuntimeError("database down")

    monkeypatch.setattr(main, "handle_feedback_submitted", broken)

    with pytest.raises(RuntimeError):
        main._on_feedback_submitted(
            EventEnvelope.build(PAYLOAD, EventType.FEEDBACK_SUBMITTED, None), PAYLOAD
        )
    assert calls == ["close"]  # the shared consumer then retries the message
