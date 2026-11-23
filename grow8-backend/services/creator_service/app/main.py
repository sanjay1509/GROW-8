import logging
import signal
import sys

from grow8_common.config import get_settings
from grow8_common.db import get_sessionmaker, wait_for_db
from grow8_common.events import (
    ApplicationSubmittedPayload,
    ApplicationWithdrawnPayload,
    EventEnvelope,
    EventType,
    FeedbackApprovedPayload,
    FeedbackRejectedPayload,
    OpportunityCreatedPayload,
    OpportunityTakenDownPayload,
    WorkSubmittedPayload,
)
from grow8_common.logging import configure_logging
from grow8_common.messaging import Handler, run_consumer
from grow8_common.models import NotificationType
from grow8_common.notifications import DbNotifier

from app.handlers.application_submitted import handle_application_submitted
from app.handlers.application_withdrawn import handle_application_withdrawn
from app.handlers.feedback_approved import handle_feedback_approved
from app.handlers.feedback_rejected import handle_feedback_rejected
from app.handlers.opportunity_created import handle_opportunity_created
from app.handlers.opportunity_taken_down import handle_opportunity_taken_down
from app.handlers.work_submitted import handle_work_submitted

SERVICE_NAME = "creator_service"

logger = logging.getLogger(__name__)


def _handle_sigterm(signum: int, frame: object) -> None:
    logger.info("received SIGTERM, shutting down")
    sys.exit(0)


def _on_opportunity_created(envelope: EventEnvelope, payload: OpportunityCreatedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.OPPORTUNITY_PUBLISHED)
        handle_opportunity_created(payload, session=session, notifier=notifier)
        # Commit before returning: the message is acked only after this handler returns.
        session.commit()


def _on_application_submitted(
    envelope: EventEnvelope, payload: ApplicationSubmittedPayload
) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.APPLICATION_SUBMITTED)
        handle_application_submitted(payload, session=session, notifier=notifier)
        session.commit()


def _on_application_withdrawn(
    envelope: EventEnvelope, payload: ApplicationWithdrawnPayload
) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.APPLICATION_WITHDRAWN)
        handle_application_withdrawn(payload, session=session, notifier=notifier)
        session.commit()


def _on_work_submitted(envelope: EventEnvelope, payload: WorkSubmittedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.WORK_SUBMITTED)
        handle_work_submitted(payload, session=session, notifier=notifier)
        session.commit()


def _on_feedback_approved(envelope: EventEnvelope, payload: FeedbackApprovedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.FEEDBACK_APPROVED)
        handle_feedback_approved(payload, session=session, notifier=notifier)
        session.commit()


def _on_feedback_rejected(envelope: EventEnvelope, payload: FeedbackRejectedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.FEEDBACK_REJECTED)
        handle_feedback_rejected(payload, session=session, notifier=notifier)
        session.commit()


def _on_opportunity_taken_down(
    envelope: EventEnvelope, payload: OpportunityTakenDownPayload
) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.OPPORTUNITY_TAKEN_DOWN)
        handle_opportunity_taken_down(payload, session=session, notifier=notifier)
        session.commit()


# Event type -> handler. Each key becomes a binding on this service's queue.
HANDLERS: dict[EventType, Handler] = {
    EventType.OPPORTUNITY_CREATED: _on_opportunity_created,
    EventType.APPLICATION_SUBMITTED: _on_application_submitted,
    EventType.APPLICATION_WITHDRAWN: _on_application_withdrawn,
    EventType.WORK_SUBMITTED: _on_work_submitted,
    EventType.FEEDBACK_APPROVED: _on_feedback_approved,
    EventType.FEEDBACK_REJECTED: _on_feedback_rejected,
    EventType.OPPORTUNITY_TAKEN_DOWN: _on_opportunity_taken_down,
}


def run() -> None:
    configure_logging(get_settings().log_level, service=SERVICE_NAME)
    signal.signal(signal.SIGTERM, _handle_sigterm)

    wait_for_db()
    logger.info("mysql reachable")

    run_consumer(SERVICE_NAME, HANDLERS)


if __name__ == "__main__":
    run()
