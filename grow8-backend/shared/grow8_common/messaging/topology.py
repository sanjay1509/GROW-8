"""RabbitMQ topology: one durable topic exchange for all events, one durable queue per
consumer service, delayed-retry queues for handler failures, and a dead-letter exchange
so a message that still can't be processed is parked in `<queue>.dlq` instead of being
lost or redelivered forever (ADR 0010).

    grow8.events ──routing key──▶ grow8.<service> ──handler fails──▶ grow8.<service>.retry.<N>s
                                        ▲                                  │ (TTL N seconds)
                                        └──────────────────────────────────┘
                                  retries used up or bad message ──▶ grow8.<service>.dlq
"""

from collections.abc import Iterable

from pika.adapters.blocking_connection import BlockingChannel

from grow8_common.config import get_settings

# Wait before each retry of a failed handler. Their sum (~2.5 min) is how long a
# dependency (usually MySQL) may be away before the message is parked in the DLQ.
# Changing a delay creates a new queue (the delay is in its name); delete the old,
# empty one from the RabbitMQ UI.
RETRY_DELAYS_SECONDS: tuple[int, ...] = (5, 30, 120)


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


def retry_queue_name(queue: str, delay_seconds: int) -> str:
    """e.g. grow8.contributor_service, 30 -> grow8.contributor_service.retry.30s"""
    return f"{queue}.retry.{delay_seconds}s"


def declare_service_queue(
    channel: BlockingChannel, service: str, routing_keys: Iterable[str]
) -> str:
    """Declare `service`'s queue, bind it to each routing key and give it retry queues
    and a dead-letter queue. Safe to call on every start: declarations are idempotent.
    Returns the queue name."""
    exchange = declare_exchange(channel)
    dlx = dead_letter_exchange_name()
    queue = service_queue_name(service)
    dlq = f"{queue}.dlq"

    channel.exchange_declare(exchange=dlx, exchange_type="direct", durable=True)
    channel.queue_declare(queue=dlq, durable=True)
    channel.queue_bind(queue=dlq, exchange=dlx, routing_key=queue)

    # A retry queue has no consumer: messages wait out its TTL, then RabbitMQ
    # dead-letters them through the default exchange ("") straight back to `queue`.
    # One queue per delay, because RabbitMQ only expires messages at the head of a
    # queue: mixing delays in one queue would hold short waits behind long ones.
    for delay in RETRY_DELAYS_SECONDS:
        channel.queue_declare(
            queue=retry_queue_name(queue, delay),
            durable=True,
            arguments={
                "x-message-ttl": delay * 1000,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": queue,
            },
        )

    channel.queue_declare(
        queue=queue,
        durable=True,
        arguments={"x-dead-letter-exchange": dlx, "x-dead-letter-routing-key": queue},
    )
    for routing_key in routing_keys:
        channel.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)
    return queue
