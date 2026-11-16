import logging
import signal
import sys

from grow8_common.config import get_settings
from grow8_common.db import get_sessionmaker, wait_for_db
from grow8_common.events import (
    ApplicationDecidedPayload,
    EventEnvelope,
    EventType,
    OpportunityCancelledPayload,
    OpportunityCreatedPayload,
)
from grow8_common.logging import configure_logging
from grow8_common.messaging import Handler, run_consumer
from grow8_common.models import NotificationType
from grow8_common.notifications import DbNotifier

from app.handlers.application_decided import handle_application_decided
from app.handlers.opportunity_cancelled import handle_opportunity_cancelled
from app.handlers.opportunity_created import handle_opportunity_created

SERVICE_NAME = "contributor_service"

logger = logging.getLogger(__name__)


def _handle_sigterm(signum: int, frame: object) -> None:
    logger.info("received SIGTERM, shutting down")
    sys.exit(0)


def _on_opportunity_created(envelope: EventEnvelope, payload: OpportunityCreatedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.OPPORTUNITY_CREATED)
        handle_opportunity_created(payload, session=session, notifier=notifier)
        # Commit before returning: the message is acked only after this handler returns.
        session.commit()


def _on_application_decided(envelope: EventEnvelope, payload: ApplicationDecidedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.APPLICATION_DECIDED)
        handle_application_decided(payload, session=session, notifier=notifier)
        session.commit()


def _on_opportunity_cancelled(
    envelope: EventEnvelope, payload: OpportunityCancelledPayload
) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.OPPORTUNITY_CANCELLED)
        handle_opportunity_cancelled(payload, session=session, notifier=notifier)
        session.commit()


# Event type -> handler. Each key becomes a binding on this service's queue.
HANDLERS: dict[EventType, Handler] = {
    EventType.OPPORTUNITY_CREATED: _on_opportunity_created,
    EventType.APPLICATION_DECIDED: _on_application_decided,
    EventType.OPPORTUNITY_CANCELLED: _on_opportunity_cancelled,
}


def run() -> None:
    configure_logging(get_settings().log_level, service=SERVICE_NAME)
    signal.signal(signal.SIGTERM, _handle_sigterm)

    wait_for_db()
    logger.info("mysql reachable")

    run_consumer(SERVICE_NAME, HANDLERS)


if __name__ == "__main__":
    run()
