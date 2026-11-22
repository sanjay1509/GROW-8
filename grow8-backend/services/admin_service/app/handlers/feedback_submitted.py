"""FEEDBACK_SUBMITTED -> tell every active admin that feedback is waiting for review
(ADR 0015). Discrepancy reports say so in the title, since admins review them first."""

import logging
from collections.abc import Callable

from grow8_common.events import FeedbackSubmittedPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import find_active_admins
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindAdmins = Callable[[Session], list[int]]


def handle_feedback_submitted(
    payload: FeedbackSubmittedPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_admins: FindAdmins = find_active_admins,
) -> list[int]:
    """Notify each active admin once and return their user_ids.

    Admins are looked up when the event is handled. The only writes are the notifier's
    (one notification per user per event), so a redelivered event adds nothing. The
    caller commits.
    """
    admin_ids = find_admins(session)
    if payload.reports_discrepancy:
        title = f"Discrepancy reported: {payload.opportunity_title}"
        message = (
            f"{payload.author_name} rated the other participant {payload.rating}/5 and "
            "reports that something on this application went wrong. Please review it."
        )
    else:
        title = f"Feedback to review: {payload.opportunity_title}"
        message = f"{payload.author_name} rated the other participant {payload.rating}/5."
    for admin_id in admin_ids:
        notifier.notify(admin_id, title, message, opportunity_id=payload.opportunity_id)
    logger.info(
        "feedback_id=%s awaiting review; notified %d admin(s): %s",
        payload.feedback_id,
        len(admin_ids),
        admin_ids,
    )
    return admin_ids
