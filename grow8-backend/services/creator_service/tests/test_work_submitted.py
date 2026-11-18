"""WORK_SUBMITTED handler, with the owner query replaced by a fake.
The real owner query is tested against MySQL in api/tests/integration/test_db_notifier.py."""

from dataclasses import dataclass
from decimal import Decimal

import pytest
from grow8_common.events import WorkSubmittedPayload

from app.handlers.work_submitted import handle_work_submitted


def _payload(hours: str = "6.50", attachments: int = 2) -> WorkSubmittedPayload:
    return WorkSubmittedPayload(
        submission_id=9,
        application_id=41,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        contributor_name="Alex Chen",
        hours_claimed=Decimal(hours),
        attachment_count=attachments,
    )


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


def _run(payload: WorkSubmittedPayload, owner_id: int | None = 2):
    notifier = RecordingNotifier()
    looked_up: list[int] = []

    def find_owner(_session, organization_id):
        looked_up.append(organization_id)
        return owner_id

    result = handle_work_submitted(payload, session=None, notifier=notifier, find_owner=find_owner)
    return result, notifier, looked_up


def test_notifies_the_owner_once() -> None:
    result, notifier, looked_up = _run(_payload())

    assert result == 2
    assert looked_up == [1]
    assert notifier.sent == [
        Sent(
            user_id=2,
            title="Work submitted: Digitize paper recipe archive",
            message="Alex Chen submitted 6.5 h of work with 2 files for you to verify.",
            opportunity_id=1,
        )
    ]


@pytest.mark.parametrize(
    ("hours", "attachments", "message"),
    [
        ("8.00", 0, "Alex Chen submitted 8 h of work for you to verify."),
        ("0.25", 1, "Alex Chen submitted 0.25 h of work with 1 file for you to verify."),
        ("10.00", 5, "Alex Chen submitted 10 h of work with 5 files for you to verify."),
    ],
)
def test_message_reads_naturally(hours: str, attachments: int, message: str) -> None:
    _, notifier, _ = _run(_payload(hours, attachments))
    [sent] = notifier.sent
    assert sent.message == message


def test_nobody_is_notified_when_the_owner_is_inactive_or_gone() -> None:
    result, notifier, _ = _run(_payload(), owner_id=None)

    assert result is None
    assert notifier.sent == []
