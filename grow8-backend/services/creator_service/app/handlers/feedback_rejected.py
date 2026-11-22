"""FEEDBACK_REJECTED -> tell the author, with the admin's reason, if the author is the
creator on the application (ADR 0015). The subject is never told."""

import logging

from grow8_common.events import FeedbackRejectedPayload
from grow8_common.notifications import Notifier
from grow8_common.notifications.feedback import rejected_notice
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def handle_feedback_rejected(
    payload: FeedbackRejectedPayload,
    *,
    session: Session,
    notifier: Notifier,
) -> int | None:
    """Notify the author once if they are the creator, and return their user_id; None if
    the author is on the other side (contributor_service tells them).

    The only write is the notifier's, so a redelivered event adds nothing. The caller
    commits.
    """
    notice = rejected_notice(payload, "creator")
    if notice is None:
        logger.info(
            "feedback_id=%s rejected; the author is not the creator, nothing to do",
            payload.feedback_id,
        )
        return None
    notifier.notify(
        notice.user_id, notice.title, notice.message, opportunity_id=payload.opportunity_id
    )
    logger.info(
        "feedback_id=%s rejected; notified creator user_id=%s", payload.feedback_id, notice.user_id
    )
    return notice.user_id
