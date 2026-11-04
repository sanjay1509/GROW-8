"""RabbitMQ topology: one durable topic exchange for all events, one durable queue per
consumer service, and a dead-letter exchange so a message that cannot be processed is
parked in `<queue>.dlq` instead of being lost or redelivered forever."""

from collections.abc import Iterable

from pika.adapters.blocking_connection import BlockingChannel

from grow8_common.config import get_settings


def declare_exchange(channel: BlockingChannel) -> str:
    """Declare the durable topic exchange all events go through; returns its name."""
    name = get_settings().rabbitmq_exchange
    channel.exchange_declare(exchange=name, exchange_type="topic", durable=True)
    return name


def dead_letter_exchange_name() -> str:
    return f"{get_settings().rabbitmq_exchange}.dlx"


def service_queue_name(service: str) -> str:
    """e.g. contributor_service -> grow8.contributor_service"""
    return f"grow8.{service}"


def declare_service_queue(
    channel: BlockingChannel, service: str, routing_keys: Iterable[str]
) -> str:
    """Declare `service`'s queue, bind it to each routing key and give it a dead-letter
    queue. Safe to call on every start: declarations are idempotent. Returns the queue name."""
    exchange = declare_exchange(channel)
    dlx = dead_letter_exchange_name()
    queue = service_queue_name(service)
    dlq = f"{queue}.dlq"

    channel.exchange_declare(exchange=dlx, exchange_type="direct", durable=True)
    channel.queue_declare(queue=dlq, durable=True)
    channel.queue_bind(queue=dlq, exchange=dlx, routing_key=queue)

    channel.queue_declare(
        queue=queue,
        durable=True,
        arguments={"x-dead-letter-exchange": dlx, "x-dead-letter-routing-key": queue},
    )
    for routing_key in routing_keys:
        channel.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)
    return queue
