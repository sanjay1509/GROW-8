"""OPPORTUNITY_TAKEN_DOWN -> tell the creator who owns the opportunity that an admin
took it down, and why (ADR 0016). Who reported it is never said."""

import logging
from collections.abc import Callable

from grow8_common.events import OpportunityTakenDownPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import find_active_owner
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindOwner = Callable[[Session, int], int | None]


def handle_opportunity_taken_down(
    payload: OpportunityTakenDownPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_owner: FindOwner = find_active_owner,
) -> int | None:
    """Notify the organization's owner once and return their user_id (None if nobody
    was notified). The only write is the notifier's, so a redelivered event adds
    nothing. The caller commits.
    """
    owner_id = find_owner(session, payload.organization_id)
    if owner_id is None:
        logger.info(
            "organization_id=%s has no active owner; nobody to notify", payload.organization_id
        )
        return None

    notifier.notify(
        owner_id,
        f"Opportunity taken down: {payload.title}",
        f'An admin took your opportunity down after reviewing reports. Reason: "{payload.reason}" '
        "Its applicants have been told it won't go ahead.",
        opportunity_id=payload.opportunity_id,
    )
    logger.info(
        "opportunity_id=%s taken down; notified creator user_id=%s",
        payload.opportunity_id,
        owner_id,
    )
    return owner_id
