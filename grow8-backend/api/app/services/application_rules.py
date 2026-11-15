"""Pure application rules (no DB, no HTTP) so they are easy to unit test.

The same rules are enforced again by triggers in db/init/001_schema.sql; these
checks exist to give a clear error before the write is attempted (ADR 0006).
"""

from datetime import datetime

from grow8_common.models import ApplicationStatus, OpportunityStatus

ACTIVE = frozenset({ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED})


def apply_refusal(
    status: OpportunityStatus,
    deadline: datetime | None,
    limit: int | None,
    active_applications: int,
    now: datetime,
) -> str | None:
    """Error code for why a new application can't be placed, or None if it can.

    Matches the trigger: only on an open opportunity, no later than its deadline,
    while pending + accepted applications are below the applicant limit."""
    if status != OpportunityStatus.OPEN:
        return "OPPORTUNITY_NOT_OPEN"
    if deadline is not None and now > deadline:
        return "APPLICATION_DEADLINE_PASSED"
    if limit is not None and active_applications >= limit:
        return "APPLICANT_LIMIT_REACHED"
    return None


def can_decide(status: ApplicationStatus) -> bool:
    """A creator decides each application once, while it is pending."""
    return status == ApplicationStatus.PENDING


def can_withdraw(status: ApplicationStatus) -> bool:
    """A contributor may withdraw while the application still holds a place
    (pending or accepted). Work already submitted is checked separately."""
    return status in ACTIVE
