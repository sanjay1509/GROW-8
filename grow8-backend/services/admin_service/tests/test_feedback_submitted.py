"""FEEDBACK_SUBMITTED handler: every active admin is told once (ADR 0015)."""

from dataclasses import dataclass

from grow8_common.events import FeedbackSubmittedPayload

from app.handlers.feedback_submitted import handle_feedback_submitted


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


def _payload(discrepancy: bool = False) -> FeedbackSubmittedPayload:
    return FeedbackSubmittedPayload(
        feedback_id=9,
        application_id=4,
        opportunity_id=1,
        opportunity_title="Digitize paper recipe archive",
        author_user_id=5,
        author_name="Alex Chen",
        author_role="contributor",
        subject_user_id=2,
        rating=4,
        reports_discrepancy=discrepancy,
    )


def test_every_active_admin_is_told() -> None:
    notifier = RecordingNotifier()

    result = handle_feedback_submitted(
        _payload(), session=None, notifier=notifier, find_admins=lambda s: [1, 50]
    )

    assert result == [1, 50]
    assert [s.user_id for s in notifier.sent] == [1, 50]
    sent = notifier.sent[0]
    assert sent.title == "Feedback to review: Digitize paper recipe archive"
    assert sent.message == "Alex Chen rated the other participant 4/5."
    assert sent.opportunity_id == 1


def test_a_discrepancy_report_says_so() -> None:
    notifier = RecordingNotifier()

    handle_feedback_submitted(
        _payload(discrepancy=True), session=None, notifier=notifier, find_admins=lambda s: [1]
    )

    [sent] = notifier.sent
    assert sent.title == "Discrepancy reported: Digitize paper recipe archive"
    assert "something on this application went wrong" in sent.message


def test_no_active_admins_notifies_nobody() -> None:
    notifier = RecordingNotifier()
    assert (
        handle_feedback_submitted(
            _payload(), session=None, notifier=notifier, find_admins=lambda s: []
        )
        == []
    )
    assert notifier.sent == []
