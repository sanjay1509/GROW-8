"""OPPORTUNITY_CREATED handler, with the database queries replaced by fakes.
The real queries are tested against MySQL in api/tests/integration/test_contributor_matching.py."""

from dataclasses import dataclass
from datetime import UTC, datetime

from grow8_common.events import OpportunityCreatedPayload
from grow8_common.queries import ContributorMatch

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


def _run(matches: list[ContributorMatch], is_open: bool = True):
    notifier = RecordingNotifier()
    seen_codes: list[list[str]] = []

    def find_matches(_session, codes):
        seen_codes.append(list(codes))
        return matches

    result = handle_opportunity_created(
        PAYLOAD,
        session=None,  # the fakes never touch it
        notifier=notifier,
        find_matches=find_matches,
        is_open=lambda _session, _id: is_open,
    )
    return result, notifier, seen_codes


def test_notifies_each_matching_contributor_once() -> None:
    matches = [
        ContributorMatch(6, "Jordan Lee", ["customer-service", "event-setup"]),
        ContributorMatch(5, "Alex Chen", ["event-setup"]),
    ]
    result, notifier, seen_codes = _run(matches)

    assert result == matches
    assert seen_codes == [["customer-service", "event-setup"]]
    assert [sent.user_id for sent in notifier.sent] == [6, 5]
    first = notifier.sent[0]
    assert first.title == "New opportunity: Volunteer coordinator for spring market"
    assert "2026-11-20" in first.message
    assert "customer-service, event-setup" in first.message
    assert first.opportunity_id == 15


def test_no_matches_sends_nothing() -> None:
    result, notifier, _ = _run([])
    assert result == []
    assert notifier.sent == []


def test_skips_opportunity_that_is_no_longer_open() -> None:
    result, notifier, seen_codes = _run(
        [ContributorMatch(6, "Jordan Lee", ["event-setup"])], is_open=False
    )
    assert result == []
    assert notifier.sent == []
    assert seen_codes == []  # no matching query once we know it's closed


def test_opportunity_without_skills_is_open_to_everyone() -> None:
    result, notifier, _ = _run([ContributorMatch(5, "Alex Chen")])
    assert len(result) == 1
    assert "open to everyone" in notifier.sent[0].message
