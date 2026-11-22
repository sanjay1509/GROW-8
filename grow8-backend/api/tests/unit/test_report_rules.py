import pytest
from grow8_common.models import OpportunityStatus, ReportDecision

from app.services.report_rules import (
    ReportStatus,
    can_be_reported,
    report_status,
    review_refusal,
    takedown_refusal,
)

UPHELD, DISMISSED = ReportDecision.UPHELD, ReportDecision.DISMISSED


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (None, ReportStatus.PENDING),
        (UPHELD, ReportStatus.UPHELD),
        (DISMISSED, ReportStatus.DISMISSED),
    ],
)
def test_status_comes_from_the_review(decision, expected) -> None:
    assert report_status(decision) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (OpportunityStatus.DRAFT, False),
        (OpportunityStatus.OPEN, True),
        (OpportunityStatus.CLOSED, True),
        (OpportunityStatus.CANCELLED, False),
    ],
)
def test_only_published_opportunities_can_be_reported(status, expected) -> None:
    assert can_be_reported(status) is expected


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_a_takedown_needs_a_reason(reason) -> None:
    assert review_refusal(UPHELD, reason) == "TAKEDOWN_REASON_REQUIRED"


def test_a_takedown_with_a_reason_is_allowed() -> None:
    assert review_refusal(UPHELD, "The pay is not what was advertised.") is None


@pytest.mark.parametrize("reason", [None, "Not misleading: the hours are listed."])
def test_a_reason_is_optional_when_dismissing(reason) -> None:
    assert review_refusal(DISMISSED, reason) is None


@pytest.mark.parametrize("status", [OpportunityStatus.OPEN, OpportunityStatus.CLOSED])
def test_published_opportunities_without_work_can_be_taken_down(status) -> None:
    assert takedown_refusal(status, work_submitted=False) is None


def test_no_takedown_once_work_is_submitted() -> None:
    assert takedown_refusal(OpportunityStatus.OPEN, work_submitted=True) == "WORK_ALREADY_SUBMITTED"


def test_no_takedown_of_a_cancelled_opportunity() -> None:
    assert (
        takedown_refusal(OpportunityStatus.CANCELLED, work_submitted=True)
        == "OPPORTUNITY_CANCELLED"
    )
