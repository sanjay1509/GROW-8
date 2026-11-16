"""APPLICATION_WITHDRAWN -> tell the creator who owns the opportunity that an applicant
withdrew, and whether that opened up an accepted place."""

import logging
from collections.abc import Callable

from grow8_common.events import ApplicationWithdrawnPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import find_active_owner
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindOwner = Callable[[Session, int], int | None]

_MESSAGE = {
    "pending": "{name} withdrew their application before you decided on it.",
    "accepted": "{name} withdrew after being accepted, so their place is open again.",
}


def handle_application_withdrawn(
    payload: ApplicationWithdrawnPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_owner: FindOwner = find_active_owner,
) -> int | None:
    """Notify the organization's owner once and return their user_id (None if nobody
    was notified).

    The status before withdrawal comes from the event, not the database: withdrawn is
    final, so the event is the only record of what it was. The only writes are the
    notifier's (one notification per user per event), so a redelivered event adds
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
        f"Application withdrawn: {payload.opportunity_title}",
        _MESSAGE[payload.previous_status].format(name=payload.contributor_name),
        opportunity_id=payload.opportunity_id,
    )
    logger.info(
        "application_id=%s withdrawn (was %s); notified creator user_id=%s",
        payload.application_id,
        payload.previous_status,
        owner_id,
    )
    return owner_id
