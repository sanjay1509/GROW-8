"""Who applied to an opportunity.

Used by contributor_service when it consumes OPPORTUNITY_CANCELLED. It lives in the
shared package so the API's integration tests can run it against the seeded test
database.
"""

from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from grow8_common.models import Application, ApplicationStatus, UserAccount


class ActiveApplicant(NamedTuple):
    user_id: int
    status: ApplicationStatus


def find_active_applicants(session: Session, opportunity_id: int) -> list[ActiveApplicant]:
    """Contributors whose application still holds a place (pending or accepted), with
    active accounts, ordered by user_id. Withdrawn and rejected applicants are left out."""
    rows = session.execute(
        select(Application.contributor_id, Application.status)
        .join(UserAccount, UserAccount.user_id == Application.contributor_id)
        .where(
            Application.opportunity_id == opportunity_id,
            Application.status.in_((ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED)),
            UserAccount.is_active.is_(True),
        )
        .order_by(Application.contributor_id)
    )
    return [ActiveApplicant(user_id, status) for user_id, status in rows]
