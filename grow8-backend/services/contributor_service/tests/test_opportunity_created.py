"""OPPORTUNITY_CREATED handler, with the database queries replaced by fakes.
The real queries are tested against MySQL in api/tests/integration/test_contributor_matching.py."""

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


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str, dict[str, object]]] = []

    def notify(self, user_id: int, message: str, **context: object) -> None:
        self.sent.append((user_id, message, context))


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
    assert [user_id for user_id, _, _ in notifier.sent] == [6, 5]
    user_id, message, context = notifier.sent[0]
    assert "Volunteer coordinator for spring market" in message
    assert "2026-11-20" in message
    assert "customer-service, event-setup" in message
    assert context == {"opportunity_id": 15, "matched_skills": 2}


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
    assert "open to everyone" in notifier.sent[0][1]
