import logging
import signal
import sys

from grow8_common.config import get_settings
from grow8_common.db import wait_for_db
from grow8_common.logging import configure_logging
from grow8_common.messaging import connect_with_retry
from pika.exceptions import AMQPError

SERVICE_NAME = "admin_service"

logger = logging.getLogger(__name__)


def _handle_sigterm(signum: int, frame: object) -> None:
    logger.info("received SIGTERM, shutting down")
    sys.exit(0)


def run() -> None:
    configure_logging(get_settings().log_level, service=SERVICE_NAME)
    signal.signal(signal.SIGTERM, _handle_sigterm)

    wait_for_db()
    logger.info("mysql reachable")

    # Placeholder loop until topology and handlers exist (build-order step g):
    # stay connected, keep heartbeats flowing, reconnect with backoff on loss.
    while True:
        connection = connect_with_retry()
        logger.info("connected to rabbitmq; no handlers registered yet")
        try:
            while True:
                connection.process_data_events(time_limit=5)
        except AMQPError as exc:
            logger.warning("rabbitmq connection lost (%s); reconnecting", type(exc).__name__)


if __name__ == "__main__":
    run()
