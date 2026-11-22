"""FEEDBACK_APPROVED and FEEDBACK_REJECTED in creator_service (ADR 0015): it notifies only
the creator: the author or the subject on approval, the author alone on rejection."""

from dataclasses import dataclass

import pytest
from grow8_common.events import FeedbackApprovedPayload, FeedbackRejectedPayload

from app import main
from app.handlers.feedback_approved import handle_feedback_approved
from app.handlers.feedback_rejected import handle_feedback_rejected

CONTRIBUTOR, CREATOR = 5, 2
COMMON = {
    "feedback_id": 9,
    "application_id": 4,
    "opportunity_id": 1,
    "opportunity_title": "Digitize paper recipe archive",
}


@dataclass(frozen=True)
class Sent:
    user_id: int
    title: str
    message: str
    opportunity_id: int | None


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[Sent] = []

    def notify(
        self, user_id: int, title: str, message: str, *, opportunity_id: int | None = None
    ) -> None:
        self.sent.append(Sent(user_id, title, message, opportunity_id))


def _approved(author_role: str) -> FeedbackApprovedPayload:
    by_contributor = author_role == "contributor"
    return FeedbackApprovedPayload(
        **COMMON,
        author_user_id=CONTRIBUTOR if by_contributor else CREATOR,
        author_name="Alex Chen" if by_contributor else "Priya Nair",
        author_role=author_role,
        subject_user_id=CREATOR if by_contributor else CONTRIBUTOR,
        subject_name="Priya Nair" if by_contributor else "Alex Chen",
        rating=4,
    )


def _rejected(author_role: str) -> FeedbackRejectedPayload:
    by_contributor = author_role == "contributor"
    return FeedbackRejectedPayload(
        **COMMON,
        author_user_id=CONTRIBUTOR if by_contributor else CREATOR,
        author_role=author_role,
        subject_name="Priya Nair" if by_contributor else "Alex Chen",
        reason="Personal remarks.",
    )


def test_approved_feedback_by_the_creator_tells_its_author() -> None:
    notifier = RecordingNotifier()

    result = handle_feedback_approved(_approved("creator"), session=None, notifier=notifier)

    [sent] = notifier.sent
    assert result == sent.user_id == CREATOR
    assert sent.title == "Your feedback was published: Digitize paper recipe archive"
    assert sent.opportunity_id == 1


def test_approved_feedback_about_the_creator_tells_its_subject() -> None:
    notifier = RecordingNotifier()

    result = handle_feedback_approved(_approved("contributor"), session=None, notifier=notifier)

    [sent] = notifier.sent
    assert result == sent.user_id == CREATOR
    assert sent.title == "New rating: Digitize paper recipe archive"
    assert "4/5" in sent.message


def test_rejected_feedback_by_the_creator_tells_its_author_why() -> None:
    notifier = RecordingNotifier()

    result = handle_feedback_rejected(_rejected("creator"), session=None, notifier=notifier)

    [sent] = notifier.sent
    assert result == sent.user_id == CREATOR
    assert sent.title == "Your feedback was not published: Digitize paper recipe archive"
    assert sent.message.endswith('Reason: "Personal remarks."')


def test_rejected_feedback_about_the_creator_tells_nobody_here() -> None:
    notifier = RecordingNotifier()

    assert (
        handle_feedback_rejected(_rejected("contributor"), session=None, notifier=notifier) is None
    )
    assert notifier.sent == []


class FakeSession:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append("close")

    def commit(self) -> None:
        self.calls.append("commit")


@pytest.mark.parametrize(
    ("on_event", "handler_name", "payload", "notification_type"),
    [
        (
            "_on_feedback_approved",
            "handle_feedback_approved",
            _approved("creator"),
            "feedback_approved",
        ),
        (
            "_on_feedback_rejected",
            "handle_feedback_rejected",
            _rejected("creator"),
            "feedback_rejected",
        ),
    ],
)
def test_wrappers_use_their_own_notification_type_then_commit(
    monkeypatch: pytest.MonkeyPatch, on_event, handler_name, payload, notification_type
) -> None:
    from grow8_common.events import EventEnvelope, EventType

    calls: list[str] = []
    seen = {}
    monkeypatch.setattr(main, "get_sessionmaker", lambda: lambda: FakeSession(calls))

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, handler_name, fake_handler)
    event_type = EventType[notification_type.upper()]

    getattr(main, on_event)(EventEnvelope.build(payload, event_type, "req-1"), payload)

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == notification_type
