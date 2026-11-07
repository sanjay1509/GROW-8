import logging

import pika
from pika.adapters.blocking_connection import BlockingConnection
from pika.exceptions import AMQPConnectionError
from tenacity import before_sleep_log, retry, retry_if_exception_type, wait_exponential

from grow8_common.config import get_settings

logger = logging.getLogger(__name__)


def connection_parameters(socket_timeout: float = 10.0) -> pika.ConnectionParameters:
    settings = get_settings()
    return pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        virtual_host=settings.rabbitmq_vhost,
        credentials=pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password),
        heartbeat=30,
        blocked_connection_timeout=60,
        socket_timeout=socket_timeout,
        connection_attempts=1,
    )


def connect(socket_timeout: float = 10.0) -> BlockingConnection:
    """Open a single connection attempt; raises on failure."""
    return pika.BlockingConnection(connection_parameters(socket_timeout))


@retry(
    retry=retry_if_exception_type(AMQPConnectionError),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def connect_with_retry() -> BlockingConnection:
    """Connect to RabbitMQ, backing off between attempts until it succeeds."""
    return connect()
