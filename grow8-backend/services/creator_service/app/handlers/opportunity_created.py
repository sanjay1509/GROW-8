"""OPPORTUNITY_CREATED -> tell the creator who published the opportunity that it is live."""

import logging
from collections.abc import Callable

from grow8_common.events import OpportunityCreatedPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import find_active_owner, is_opportunity_open
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindOwner = Callable[[Session, int], int | None]
IsOpen = Callable[[Session, int], bool]


def handle_opportunity_created(
    payload: OpportunityCreatedPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_owner: FindOwner = find_active_owner,
    is_open: IsOpen = is_opportunity_open,
) -> int | None:
    """Notify the organization's owner once and return their user_id (None if nobody
    was notified).

    The only writes are the notifier's, and it stores one notification per user per
    event, so handling the same event twice (at-least-once delivery) adds nothing.
    The caller commits.
    """
    if not is_open(session, payload.opportunity_id):
        logger.info(
            "opportunity_id=%s is no longer open; not telling the creator it is live",
            payload.opportunity_id,
        )
        return None

    owner_id = find_owner(session, payload.organization_id)
    if owner_id is None:
        logger.info(
            "organization_id=%s has no active owner; nobody to notify", payload.organization_id
        )
        return None

    deadline = payload.application_deadline.strftime("%Y-%m-%d %H:%M UTC")
    notifier.notify(
        owner_id,
        f"Your opportunity is live: {payload.title}",
        f"Contributors can now find it and apply until {deadline}.",
        opportunity_id=payload.opportunity_id,
    )
    logger.info("opportunity_id=%s notified creator user_id=%s", payload.opportunity_id, owner_id)
    return owner_id
