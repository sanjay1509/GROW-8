"""OPPORTUNITY_CANCELLED -> tell everyone whose application still held a place
(pending or accepted) that the opportunity won't happen."""

import logging
from collections.abc import Callable

from grow8_common.events import OpportunityCancelledPayload
from grow8_common.models import ApplicationStatus
from grow8_common.notifications import Notifier
from grow8_common.queries import ActiveApplicant, find_active_applicants
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindApplicants = Callable[[Session, int], list[ActiveApplicant]]

_MESSAGE = {
    ApplicationStatus.PENDING: (
        "The organization cancelled this opportunity, so your application won't be decided."
    ),
    ApplicationStatus.ACCEPTED: (
        "The organization cancelled this opportunity you were accepted for. "
        "You don't need to do anything."
    ),
}


def handle_opportunity_cancelled(
    payload: OpportunityCancelledPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_applicants: FindApplicants = find_active_applicants,
) -> list[int]:
    """Notify each pending or accepted applicant once and return their user_ids.

    Applicants are looked up now, not listed in the event: anyone who withdrew in the
    meantime has nothing to be told. Statuses can't change after a cancel (deciding is
    refused), so a redelivery finds the same people, and the notifier stores one
    notification per user per event, so it adds nothing. The caller commits.
    """
    applicants = find_applicants(session, payload.opportunity_id)
    for applicant in applicants:
        notifier.notify(
            applicant.user_id,
            f"Opportunity cancelled: {payload.title}",
            _MESSAGE[applicant.status],
            opportunity_id=payload.opportunity_id,
        )

    notified = [a.user_id for a in applicants]
    logger.info(
        "opportunity_id=%s cancelled; notified %d applicant(s): %s",
        payload.opportunity_id,
        len(notified),
        notified,
    )
    return notified
