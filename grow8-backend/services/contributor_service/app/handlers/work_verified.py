"""WORK_VERIFIED -> tell the contributor their work was approved, with the hours
verified (ADR 0013).

Verified hours and verified skills are derived from approved verifications by the
views (v_contributor_verified_hours, v_contributor_skill), so nothing else is stored
here. Points and badges (#24) will extend this handler.
"""

import logging
from decimal import Decimal

from grow8_common.events import WorkVerifiedPayload
from grow8_common.notifications import Notifier
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _hours(hours: Decimal) -> str:
    """6.50 -> "6.5", 8.00 -> "8"."""
    return f"{hours.normalize():f}"


def handle_work_verified(
    payload: WorkVerifiedPayload,
    *,
    session: Session,
    notifier: Notifier,
) -> int:
    """Notify the contributor once and return their user_id.

    Each submission is verified once and the decision is final, so it is taken from the
    event rather than re-read. The only write is the notifier's (one notification per
    user per event), so a redelivered event adds nothing. The caller commits.
    """
    notifier.notify(
        payload.contributor_id,
        f"Work verified: {payload.opportunity_title}",
        f"Your work on {payload.opportunity_title} was verified "
        f"({_hours(payload.verified_hours)} h). It now counts toward your verified hours.",
        opportunity_id=payload.opportunity_id,
    )
    logger.info(
        "verification_id=%s for submission_id=%s approved; notified contributor user_id=%s",
        payload.verification_id,
        payload.submission_id,
        payload.contributor_id,
    )
    return payload.contributor_id
