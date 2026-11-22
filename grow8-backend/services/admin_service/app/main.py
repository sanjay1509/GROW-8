import logging
import signal
import sys

from grow8_common.config import get_settings
from grow8_common.db import get_sessionmaker, wait_for_db
from grow8_common.events import (
    EventEnvelope,
    EventType,
    FeedbackSubmittedPayload,
    OpportunityReportedPayload,
)
from grow8_common.logging import configure_logging
from grow8_common.messaging import Handler, run_consumer
from grow8_common.models import NotificationType
from grow8_common.notifications import DbNotifier

from app.handlers.feedback_submitted import handle_feedback_submitted
from app.handlers.opportunity_reported import handle_opportunity_reported

SERVICE_NAME = "admin_service"

logger = logging.getLogger(__name__)


def _handle_sigterm(signum: int, frame: object) -> None:
    logger.info("received SIGTERM, shutting down")
    sys.exit(0)


def _on_feedback_submitted(envelope: EventEnvelope, payload: FeedbackSubmittedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.FEEDBACK_SUBMITTED)
        handle_feedback_submitted(payload, session=session, notifier=notifier)
        # Commit before returning: the message is acked only after this handler returns.
        session.commit()


def _on_opportunity_reported(envelope: EventEnvelope, payload: OpportunityReportedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.OPPORTUNITY_REPORTED)
        handle_opportunity_reported(payload, session=session, notifier=notifier)
        session.commit()


# Event type -> handler. Each key becomes a binding on this service's queue
# (grow8.admin_service, with its retry queues and dead-letter queue, ADR 0010).
HANDLERS: dict[EventType, Handler] = {
    EventType.FEEDBACK_SUBMITTED: _on_feedback_submitted,
    EventType.OPPORTUNITY_REPORTED: _on_opportunity_reported,
}


def run() -> None:
    configure_logging(get_settings().log_level, service=SERVICE_NAME)
    signal.signal(signal.SIGTERM, _handle_sigterm)

    wait_for_db()
    logger.info("mysql reachable")

    run_consumer(SERVICE_NAME, HANDLERS)


if __name__ == "__main__":
    run()
