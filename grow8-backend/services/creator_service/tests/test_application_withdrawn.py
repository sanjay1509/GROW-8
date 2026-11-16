"""APPLICATION_WITHDRAWN handler, with the owner query replaced by a fake.
The real owner query is tested against MySQL in api/tests/integration/test_db_notifier.py."""

from dataclasses import dataclass

import pytest
from grow8_common.events import ApplicationWithdrawnPayload
from pydantic import ValidationError

from app.handlers.application_withdrawn import handle_application_withdrawn


def _payload(previous_status: str = "pending") -> ApplicationWithdrawnPayload:
    return ApplicationWithdrawnPayload(
        application_id=41,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        contributor_name="Alex Chen",
        previous_status=previous_status,
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


def _run(payload: ApplicationWithdrawnPayload, owner_id: int | None = 2):
    notifier = RecordingNotifier()
    looked_up: list[int] = []

    def find_owner(_session, organization_id):
        looked_up.append(organization_id)
        return owner_id

    result = handle_application_withdrawn(
        payload, session=None, notifier=notifier, find_owner=find_owner
    )
    return result, notifier, looked_up


def test_pending_withdrawal_notifies_the_owner_once() -> None:
    result, notifier, looked_up = _run(_payload("pending"))

    assert result == 2
    assert looked_up == [1]
    assert notifier.sent == [
        Sent(
            user_id=2,
            title="Application withdrawn: Digitize paper recipe archive",
            message="Alex Chen withdrew their application before you decided on it.",
            opportunity_id=1,
        )
    ]


def test_accepted_withdrawal_says_the_place_is_open_again() -> None:
    _, notifier, _ = _run(_payload("accepted"))

    [sent] = notifier.sent
    assert sent.message == "Alex Chen withdrew after being accepted, so their place is open again."


def test_nobody_is_notified_when_the_owner_is_inactive_or_gone() -> None:
    result, notifier, _ = _run(_payload(), owner_id=None)

    assert result is None
    assert notifier.sent == []


@pytest.mark.parametrize("status", ["rejected", "withdrawn"])
def test_payload_only_allows_withdrawable_statuses(status: str) -> None:
    with pytest.raises(ValidationError):
        _payload(status)
