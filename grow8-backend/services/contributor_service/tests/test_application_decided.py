"""APPLICATION_DECIDED handler: the applicant is told the decision once."""

from dataclasses import dataclass

import pytest
from grow8_common.events import ApplicationDecidedPayload

from app.handlers.application_decided import handle_application_decided


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


def _payload(decision: str) -> ApplicationDecidedPayload:
    return ApplicationDecidedPayload(
        application_id=41,
        opportunity_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        decision=decision,
    )


@pytest.mark.parametrize(
    ("decision", "title"),
    [
        ("accepted", "You were accepted: Digitize paper recipe archive"),
        ("rejected", "Application update: Digitize paper recipe archive"),
    ],
)
def test_tells_the_applicant_the_decision(decision: str, title: str) -> None:
    notifier = RecordingNotifier()

    result = handle_application_decided(_payload(decision), session=None, notifier=notifier)

    assert result == 5
    [sent] = notifier.sent
    assert (sent.user_id, sent.title, sent.opportunity_id) == (5, title, 1)


def test_only_accepted_or_rejected_are_valid_decisions() -> None:
    with pytest.raises(ValueError):
        _payload("withdrawn")
