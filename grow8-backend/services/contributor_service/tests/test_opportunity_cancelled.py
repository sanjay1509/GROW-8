"""OPPORTUNITY_CANCELLED handler, with the applicant query replaced by a fake.
The real query is tested against MySQL in api/tests/integration/test_db_notifier.py."""

from dataclasses import dataclass

from grow8_common.events import OpportunityCancelledPayload
from grow8_common.models import ApplicationStatus
from grow8_common.queries import ActiveApplicant

from app.handlers.opportunity_cancelled import handle_opportunity_cancelled

PAYLOAD = OpportunityCancelledPayload(
    opportunity_id=1, organization_id=1, title="Digitize paper recipe archive"
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


def _run(applicants: list[ActiveApplicant]):
    notifier = RecordingNotifier()
    looked_up: list[int] = []

    def find_applicants(_session, opportunity_id):
        looked_up.append(opportunity_id)
        return applicants

    result = handle_opportunity_cancelled(
        PAYLOAD, session=None, notifier=notifier, find_applicants=find_applicants
    )
    return result, notifier, looked_up


def test_pending_and_accepted_applicants_are_each_told_once() -> None:
    result, notifier, looked_up = _run(
        [
            ActiveApplicant(5, ApplicationStatus.PENDING),
            ActiveApplicant(6, ApplicationStatus.ACCEPTED),
        ]
    )

    assert result == [5, 6]
    assert looked_up == [1]
    assert notifier.sent == [
        Sent(
            5,
            "Opportunity cancelled: Digitize paper recipe archive",
            "The organization cancelled this opportunity, so your application won't be decided.",
            1,
        ),
        Sent(
            6,
            "Opportunity cancelled: Digitize paper recipe archive",
            "The organization cancelled this opportunity you were accepted for. "
            "You don't need to do anything.",
            1,
        ),
    ]


def test_nobody_to_tell_when_no_application_holds_a_place() -> None:
    result, notifier, _ = _run([])

    assert result == []
    assert notifier.sent == []
