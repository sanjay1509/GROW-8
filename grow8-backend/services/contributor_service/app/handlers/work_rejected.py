"""WORK_REJECTED -> tell the contributor their work was not verified, with the
creator's comment (ADR 0013)."""

import logging

from grow8_common.events import WorkRejectedPayload
from grow8_common.notifications import Notifier
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def handle_work_rejected(
    payload: WorkRejectedPayload,
    *,
    session: Session,
    notifier: Notifier,
) -> int:
    """Notify the contributor once and return their user_id.

    The comment is quoted as the creator wrote it. A long one is shortened by the
    notifier to fit the message; the full comment is on the submission. The only write
    is the notifier's, so a redelivered event adds nothing. The caller commits.
    """
    notifier.notify(
        payload.contributor_id,
        f"Work not verified: {payload.opportunity_title}",
        f'The organization did not verify your work. Their comment: "{payload.comment}"',
        opportunity_id=payload.opportunity_id,
    )
    logger.info(
        "verification_id=%s for submission_id=%s rejected; notified contributor user_id=%s",
        payload.verification_id,
        payload.submission_id,
        payload.contributor_id,
    )
    return payload.contributor_id
