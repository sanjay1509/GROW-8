"""WORK_SUBMITTED -> tell the creator who owns the opportunity that an applicant's work
is waiting for their verification (ADR 0012)."""

import logging
from collections.abc import Callable
from decimal import Decimal

from grow8_common.events import WorkSubmittedPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import find_active_owner
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindOwner = Callable[[Session, int], int | None]


def _hours(hours: Decimal) -> str:
    """6.50 -> "6.5", 8.00 -> "8"."""
    return f"{hours.normalize():f}"


def _files(count: int) -> str:
    if count == 0:
        return ""
    return f" with {count} file" + ("" if count == 1 else "s")


def handle_work_submitted(
    payload: WorkSubmittedPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_owner: FindOwner = find_active_owner,
) -> int | None:
    """Notify the organization's owner once and return their user_id (None if nobody
    was notified).

    The only writes are the notifier's (one notification per user per event), so a
    redelivered event adds nothing. The caller commits.
    """
    owner_id = find_owner(session, payload.organization_id)
    if owner_id is None:
        logger.info(
            "organization_id=%s has no active owner; nobody to notify", payload.organization_id
        )
        return None

    notifier.notify(
        owner_id,
        f"Work submitted: {payload.opportunity_title}",
        f"{payload.contributor_name} submitted {_hours(payload.hours_claimed)} h of work"
        f"{_files(payload.attachment_count)} for you to verify.",
        opportunity_id=payload.opportunity_id,
    )
    logger.info(
        "submission_id=%s for application_id=%s; notified creator user_id=%s",
        payload.submission_id,
        payload.application_id,
        owner_id,
    )
    return owner_id
