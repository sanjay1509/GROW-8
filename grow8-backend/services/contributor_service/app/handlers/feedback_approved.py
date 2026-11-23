"""FEEDBACK_APPROVED -> tell the contributor on the application: the author that their
feedback was published, or the subject that they received a rating (ADR 0015). The
creator side is told by creator_service."""

import logging

from grow8_common.events import FeedbackApprovedPayload
from grow8_common.notifications import Notifier
from grow8_common.notifications.feedback import approved_notice
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def handle_feedback_approved(
    payload: FeedbackApprovedPayload,
    *,
    session: Session,
    notifier: Notifier,
) -> int:
    """Notify the contributor once and return their user_id.

    The review is final, so it is taken from the event rather than re-read. The only
    write is the notifier's (one notification per user per event), so a redelivered
    event adds nothing. The caller commits.
    """
    notice = approved_notice(payload, "contributor")
    notifier.notify(
        notice.user_id, notice.title, notice.message, opportunity_id=payload.opportunity_id
    )
    logger.info(
        "feedback_id=%s approved; notified contributor user_id=%s",
        payload.feedback_id,
        notice.user_id,
    )
    return notice.user_id
