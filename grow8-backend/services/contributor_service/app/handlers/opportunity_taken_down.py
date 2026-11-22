"""OPPORTUNITY_TAKEN_DOWN -> tell the pending and accepted applicants that the
opportunity won't go ahead, and thank the contributors who reported it (ADR 0016).

The admin's reason was written for the creator, so it isn't repeated to contributors.
"""

import logging
from collections.abc import Callable

from grow8_common.events import OpportunityTakenDownPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import ActiveApplicant, find_active_applicants
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindApplicants = Callable[[Session, int], list[ActiveApplicant]]

APPLICANT_MESSAGE = (
    "An admin took this opportunity down after reviewing reports, so your application "
    "won't go ahead. You don't need to do anything."
)
REPORTER_MESSAGE = "An admin reviewed the reports and took this opportunity down."


def handle_opportunity_taken_down(
    payload: OpportunityTakenDownPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_applicants: FindApplicants = find_active_applicants,
) -> list[int]:
    """Notify each applicant and reporter once and return their user_ids, in id order.

    A reporter who also applied gets the reporter message only, so everyone gets one
    notification for this event. Applicants are looked up now (statuses can't change
    after a takedown); the reporters come from the event. The only writes are the
    notifier's, so a redelivered event adds nothing. The caller commits.
    """
    messages: dict[int, tuple[str, str]] = {}
    for applicant in find_applicants(session, payload.opportunity_id):
        messages[applicant.user_id] = (
            f"Opportunity taken down: {payload.title}",
            APPLICANT_MESSAGE,
        )
    for reporter_id in payload.reporter_user_ids:
        messages[reporter_id] = (f"Thanks for your report: {payload.title}", REPORTER_MESSAGE)

    notified = sorted(messages)
    for user_id in notified:
        title, message = messages[user_id]
        notifier.notify(user_id, title, message, opportunity_id=payload.opportunity_id)
    logger.info(
        "opportunity_id=%s taken down; notified %d contributor(s): %s",
        payload.opportunity_id,
        len(notified),
        notified,
    )
    return notified
