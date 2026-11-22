"""OPPORTUNITY_REPORTED -> tell every active admin that an opportunity was reported
(ADR 0016). The reporter isn't named here; admins see who reported in the queue."""

import logging
from collections.abc import Callable

from grow8_common.events import OpportunityReportedPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import find_active_admins
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindAdmins = Callable[[Session], list[int]]

REASONS = {
    "misleading_terms": "misleading terms",
    "unsafe_conditions": "unsafe conditions",
    "discriminatory": "discriminatory",
    "scam_or_spam": "a scam or spam",
    "other": "another reason",
}


def _open(count: int) -> str:
    return "1 open report" if count == 1 else f"{count} open reports"


def handle_opportunity_reported(
    payload: OpportunityReportedPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_admins: FindAdmins = find_active_admins,
) -> list[int]:
    """Notify each active admin once and return their user_ids.

    The only writes are the notifier's (one notification per user per event), so a
    redelivered event adds nothing. The caller commits.
    """
    admin_ids = find_admins(session)
    title = f"Opportunity reported: {payload.opportunity_title}"
    message = (
        f"A contributor reported it as {REASONS[payload.reason]}. "
        f"It has {_open(payload.open_reports)}."
    )
    for admin_id in admin_ids:
        notifier.notify(admin_id, title, message, opportunity_id=payload.opportunity_id)
    logger.info(
        "report_id=%s on opportunity_id=%s; notified %d admin(s): %s",
        payload.report_id,
        payload.opportunity_id,
        len(admin_ids),
        admin_ids,
    )
    return admin_ids
