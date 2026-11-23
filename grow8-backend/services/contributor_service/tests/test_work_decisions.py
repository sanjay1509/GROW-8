"""WORK_VERIFIED and WORK_REJECTED handlers (ADR 0013): the contributor is told the
outcome once, with the hours verified or the creator's comment."""

from dataclasses import dataclass
from decimal import Decimal

from grow8_common.events import WorkRejectedPayload, WorkVerifiedPayload

from app.handlers.work_rejected import handle_work_rejected
from app.handlers.work_verified import handle_work_verified

COMMON = {
    "verification_id": 7,
    "submission_id": 3,
    "application_id": 4,
    "opportunity_id": 1,
    "organization_id": 1,
    "opportunity_title": "Digitize paper recipe archive",
    "contributor_id": 5,
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


def _verified(hours: str) -> WorkVerifiedPayload:
    return WorkVerifiedPayload(**COMMON, verified_hours=Decimal(hours))


def test_verified_work_tells_the_contributor_the_hours() -> None:
    notifier = RecordingNotifier()

    result = handle_work_verified(_verified("6.00"), session=None, notifier=notifier)

    assert result == 5
    [sent] = notifier.sent
    assert (sent.user_id, sent.opportunity_id) == (5, 1)
    assert sent.title == "Work verified: Digitize paper recipe archive"
    assert sent.message.startswith("Your work on Digitize paper recipe archive was verified (6 h).")


def test_partial_hours_read_naturally() -> None:
    notifier = RecordingNotifier()

    handle_work_verified(_verified("5.50"), session=None, notifier=notifier)

    assert "(5.5 h)" in notifier.sent[0].message


def test_rejected_work_quotes_the_creators_comment() -> None:
    notifier = RecordingNotifier()
    payload = WorkRejectedPayload(**COMMON, comment="Half the recipes are missing.")

    result = handle_work_rejected(payload, session=None, notifier=notifier)

    assert result == 5
    [sent] = notifier.sent
    assert (sent.user_id, sent.opportunity_id) == (5, 1)
    assert sent.title == "Work not verified: Digitize paper recipe archive"
    assert sent.message == (
        'The organization did not verify your work. Their comment: "Half the recipes are missing."'
    )
