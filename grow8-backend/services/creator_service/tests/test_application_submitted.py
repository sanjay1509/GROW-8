"""APPLICATION_SUBMITTED handler, with the owner query replaced by a fake.
The real owner query is tested against MySQL in api/tests/integration/test_db_notifier.py."""

from dataclasses import dataclass

from grow8_common.events import ApplicationSubmittedPayload

from app.handlers.application_submitted import handle_application_submitted

PAYLOAD = ApplicationSubmittedPayload(
    application_id=41,
    opportunity_id=1,
    organization_id=1,
    opportunity_title="Digitize paper recipe archive",
    contributor_id=5,
    contributor_name="Alex Chen",
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


def _run(owner_id: int | None = 2):
    notifier = RecordingNotifier()
    looked_up: list[int] = []

    def find_owner(_session, organization_id):
        looked_up.append(organization_id)
        return owner_id

    result = handle_application_submitted(
        PAYLOAD, session=None, notifier=notifier, find_owner=find_owner
    )
    return result, notifier, looked_up


def test_notifies_the_organization_owner_once() -> None:
    result, notifier, looked_up = _run(owner_id=2)

    assert result == 2
    assert looked_up == [1]
    assert notifier.sent == [
        Sent(
            user_id=2,
            title="New application: Digitize paper recipe archive",
            message="Alex Chen applied. Review the application to accept or reject it.",
            opportunity_id=1,
        )
    ]


def test_nobody_is_notified_when_the_owner_is_inactive_or_gone() -> None:
    result, notifier, _ = _run(owner_id=None)

    assert result is None
    assert notifier.sent == []
