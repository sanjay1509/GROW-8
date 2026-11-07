"""OPPORTUNITY_CREATED handler, with the database queries replaced by fakes.
The real owner query is tested against MySQL in api/tests/integration/test_db_notifier.py."""

from dataclasses import dataclass
from datetime import UTC, datetime

from grow8_common.events import OpportunityCreatedPayload

from app.handlers.opportunity_created import handle_opportunity_created

PAYLOAD = OpportunityCreatedPayload(
    opportunity_id=15,
    organization_id=3,
    title="Volunteer coordinator for spring market",
    category_code="community",
    application_deadline=datetime(2026, 11, 20, 23, 59, tzinfo=UTC),
    skill_codes=["customer-service", "event-setup"],
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


def _run(owner_id: int | None = 4, is_open: bool = True):
    notifier = RecordingNotifier()
    looked_up: list[int] = []

    def find_owner(_session, organization_id):
        looked_up.append(organization_id)
        return owner_id

    result = handle_opportunity_created(
        PAYLOAD,
        session=None,  # the fakes never touch it
        notifier=notifier,
        find_owner=find_owner,
        is_open=lambda _session, _id: is_open,
    )
    return result, notifier, looked_up


def test_notifies_the_organization_owner_once() -> None:
    result, notifier, looked_up = _run(owner_id=4)

    assert result == 4
    assert looked_up == [3]
    assert notifier.sent == [
        Sent(
            4,
            "Your opportunity is live: Volunteer coordinator for spring market",
            "Contributors can now find it and apply until 2026-11-20 23:59 UTC.",
            15,
        )
    ]


def test_no_active_owner_sends_nothing() -> None:
    result, notifier, _ = _run(owner_id=None)
    assert result is None
    assert notifier.sent == []


def test_skips_opportunity_that_is_no_longer_open() -> None:
    result, notifier, looked_up = _run(is_open=False)
    assert result is None
    assert notifier.sent == []
    assert looked_up == []  # no owner query once we know it's closed
