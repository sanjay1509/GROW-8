"""REPORT_DISMISSED -> tell the contributor who reported that an admin reviewed their
report and left the opportunity up, with the admin's note if there is one (ADR 0016)."""

import logging

from grow8_common.events import ReportDismissedPayload
from grow8_common.notifications import Notifier
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def handle_report_dismissed(
    payload: ReportDismissedPayload,
    *,
    session: Session,
    notifier: Notifier,
) -> int:
    """Notify the reporter once and return their user_id. The only write is the
    notifier's, so a redelivered event adds nothing. The caller commits."""
    message = "An admin reviewed your report and decided the opportunity can stay up."
    if payload.reason:
        message += f' Their note: "{payload.reason}"'
    notifier.notify(
        payload.reporter_user_id,
        f"Report reviewed: {payload.opportunity_title}",
        message,
        opportunity_id=payload.opportunity_id,
    )
    logger.info(
        "report_id=%s dismissed; notified reporter user_id=%s",
        payload.report_id,
        payload.reporter_user_id,
    )
    return payload.reporter_user_id
