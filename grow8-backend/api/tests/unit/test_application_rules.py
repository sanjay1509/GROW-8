from datetime import datetime

import pytest
from grow8_common.models import ApplicationStatus, OpportunityStatus

from app.services.application_rules import apply_refusal, can_decide, can_withdraw

NOW = datetime(2026, 10, 16, 12, 0)
DEADLINE = datetime(2026, 11, 20, 23, 59, 59)


def test_open_opportunity_with_places_accepts_applications() -> None:
    assert apply_refusal(OpportunityStatus.OPEN, DEADLINE, 2, 1, NOW) is None


@pytest.mark.parametrize(
    "status", [OpportunityStatus.DRAFT, OpportunityStatus.CLOSED, OpportunityStatus.CANCELLED]
)
def test_only_open_opportunities_accept_applications(status: OpportunityStatus) -> None:
    assert apply_refusal(status, DEADLINE, 2, 0, NOW) == "OPPORTUNITY_NOT_OPEN"


def test_applying_exactly_at_the_deadline_is_allowed_like_the_trigger() -> None:
    assert apply_refusal(OpportunityStatus.OPEN, NOW, 2, 0, NOW) is None
    later = datetime(2026, 10, 16, 12, 0, 1)
    assert apply_refusal(OpportunityStatus.OPEN, NOW, 2, 0, later) == "APPLICATION_DEADLINE_PASSED"


def test_limit_counts_active_applications() -> None:
    assert apply_refusal(OpportunityStatus.OPEN, DEADLINE, 2, 2, NOW) == "APPLICANT_LIMIT_REACHED"


def test_closed_status_is_reported_before_deadline_or_limit() -> None:
    assert apply_refusal(OpportunityStatus.CLOSED, NOW, 1, 5, DEADLINE) == "OPPORTUNITY_NOT_OPEN"


def test_only_pending_applications_can_be_decided() -> None:
    assert [s for s in ApplicationStatus if can_decide(s)] == [ApplicationStatus.PENDING]


def test_pending_and_accepted_applications_can_be_withdrawn() -> None:
    assert {s for s in ApplicationStatus if can_withdraw(s)} == {
        ApplicationStatus.PENDING,
        ApplicationStatus.ACCEPTED,
    }
