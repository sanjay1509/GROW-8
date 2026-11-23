"""Pure opportunity-report rules (no DB, no HTTP) so they are easy to unit test
(ADR 0016).

A report's status is derived, never stored: pending until it has a `report_review` row,
then the review's decision.
"""

from enum import StrEnum

from grow8_common.models import OpportunityStatus, ReportDecision

PUBLISHED = frozenset({OpportunityStatus.OPEN, OpportunityStatus.CLOSED})


class ReportStatus(StrEnum):
    PENDING = "pending"
    UPHELD = "upheld"
    DISMISSED = "dismissed"


def report_status(decision: ReportDecision | None) -> ReportStatus:
    """A report's status from its review's decision (None: not reviewed yet)."""
    if decision is None:
        return ReportStatus.PENDING
    return ReportStatus(decision.value)


def can_be_reported(status: OpportunityStatus) -> bool:
    """Only published opportunities (open or closed) can be reported. A draft is
    treated as missing by the caller; a cancelled one gets OPPORTUNITY_CANCELLED."""
    return status in PUBLISHED


def review_refusal(decision: ReportDecision, reason: str | None) -> str | None:
    """Error code for why this review can't be recorded, or None if it can. A takedown
    always says why, because the creator is told the reason."""
    if decision == ReportDecision.UPHELD and not (reason and reason.strip()):
        return "TAKEDOWN_REASON_REQUIRED"
    return None


def takedown_refusal(status: OpportunityStatus, work_submitted: bool) -> str | None:
    """Error code for why the opportunity can't be taken down, or None if it can.

    Not once its creator cancelled it, and not once work was submitted for it: cancelling
    is refused then (ADR 0011), and verification refuses cancelled opportunities (ADR 0013).
    """
    if status == OpportunityStatus.CANCELLED:
        return "OPPORTUNITY_CANCELLED"
    if work_submitted:
        return "WORK_ALREADY_SUBMITTED"
    return None
