import logging
import signal
import sys

from grow8_common.config import get_settings
from grow8_common.db import get_sessionmaker, wait_for_db
from grow8_common.events import (
    ApplicationDecidedPayload,
    EventEnvelope,
    EventType,
    FeedbackApprovedPayload,
    FeedbackRejectedPayload,
    OpportunityCancelledPayload,
    OpportunityCreatedPayload,
    OpportunityTakenDownPayload,
    ReportDismissedPayload,
    WorkRejectedPayload,
    WorkVerifiedPayload,
)
from grow8_common.logging import configure_logging
from grow8_common.messaging import Handler, run_consumer
from grow8_common.models import NotificationType
from grow8_common.notifications import DbNotifier

from app.handlers.application_decided import handle_application_decided
from app.handlers.feedback_approved import handle_feedback_approved
from app.handlers.feedback_rejected import handle_feedback_rejected
from app.handlers.opportunity_cancelled import handle_opportunity_cancelled
from app.handlers.opportunity_created import handle_opportunity_created
from app.handlers.opportunity_taken_down import handle_opportunity_taken_down
from app.handlers.report_dismissed import handle_report_dismissed
from app.handlers.work_rejected import handle_work_rejected
from app.handlers.work_verified import handle_work_verified

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


def _on_work_verified(envelope: EventEnvelope, payload: WorkVerifiedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.WORK_VERIFIED)
        handle_work_verified(payload, session=session, notifier=notifier)
        session.commit()


def _on_work_rejected(envelope: EventEnvelope, payload: WorkRejectedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.WORK_REJECTED)
        handle_work_rejected(payload, session=session, notifier=notifier)
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


def _on_report_dismissed(envelope: EventEnvelope, payload: ReportDismissedPayload) -> None:
    with get_sessionmaker()() as session:
        notifier = DbNotifier(session, envelope.event_id, NotificationType.REPORT_DISMISSED)
        handle_report_dismissed(payload, session=session, notifier=notifier)
        session.commit()


# Event type -> handler. Each key becomes a binding on this service's queue.
HANDLERS: dict[EventType, Handler] = {
    EventType.OPPORTUNITY_CREATED: _on_opportunity_created,
    EventType.APPLICATION_DECIDED: _on_application_decided,
    EventType.OPPORTUNITY_CANCELLED: _on_opportunity_cancelled,
    EventType.WORK_VERIFIED: _on_work_verified,
    EventType.WORK_REJECTED: _on_work_rejected,
    EventType.FEEDBACK_APPROVED: _on_feedback_approved,
    EventType.FEEDBACK_REJECTED: _on_feedback_rejected,
    EventType.OPPORTUNITY_TAKEN_DOWN: _on_opportunity_taken_down,
    EventType.REPORT_DISMISSED: _on_report_dismissed,
}


def run() -> None:
    configure_logging(get_settings().log_level, service=SERVICE_NAME)
    signal.signal(signal.SIGTERM, _handle_sigterm)

    wait_for_db()
    logger.info("mysql reachable")

    run_consumer(SERVICE_NAME, HANDLERS)


if __name__ == "__main__":
    run()
