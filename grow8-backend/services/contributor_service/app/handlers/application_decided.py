"""APPLICATION_DECIDED -> tell the contributor whether they were accepted or rejected."""

import logging

from grow8_common.events import ApplicationDecidedPayload
from grow8_common.notifications import Notifier
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_TEXT = {
    "accepted": (
        "You were accepted: {title}",
        "The organization accepted your application. They will contact you about next steps.",
    ),
    "rejected": (
        "Application update: {title}",
        "The organization did not select you this time. Keep exploring other opportunities.",
    ),
}


def handle_application_decided(
    payload: ApplicationDecidedPayload,
    *,
    session: Session,
    notifier: Notifier,
) -> int:
    """Notify the applicant once and return their user_id.

    The decision in the event is final (each application is decided once), so it is
    not re-read from the database. The only write is the notifier's, which stores one
    notification per user per event, so a redelivered event adds nothing.
    The caller commits.
    """
    title, message = _TEXT[payload.decision]
    notifier.notify(
        payload.contributor_id,
        title.format(title=payload.opportunity_title),
        message,
        opportunity_id=payload.opportunity_id,
    )
    logger.info(
        "application_id=%s decision=%s notified contributor user_id=%s",
        payload.application_id,
        payload.decision,
        payload.contributor_id,
    )
    return payload.contributor_id
