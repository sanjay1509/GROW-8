"""APPLICATION_SUBMITTED -> tell the creator who owns the opportunity that someone applied."""

import logging
from collections.abc import Callable

from grow8_common.events import ApplicationSubmittedPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import find_active_owner
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindOwner = Callable[[Session, int], int | None]


def handle_application_submitted(
    payload: ApplicationSubmittedPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_owner: FindOwner = find_active_owner,
) -> int | None:
    """Notify the organization's owner once and return their user_id (None if nobody
    was notified).

    The only writes are the notifier's, and it stores one notification per user per
    event, so handling the same event twice (at-least-once delivery) adds nothing.
    The caller commits.
    """
    owner_id = find_owner(session, payload.organization_id)
    if owner_id is None:
        logger.info(
            "organization_id=%s has no active owner; nobody to notify", payload.organization_id
        )
        return None

    notifier.notify(
        owner_id,
        f"New application: {payload.opportunity_title}",
        f"{payload.contributor_name} applied. Review the application to accept or reject it.",
        opportunity_id=payload.opportunity_id,
    )
    logger.info("application_id=%s notified creator user_id=%s", payload.application_id, owner_id)
    return owner_id
