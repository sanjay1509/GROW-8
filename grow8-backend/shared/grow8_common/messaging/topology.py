"""RabbitMQ topology. Per-service queues, bindings and dead-lettering are added
with the consumers (build-order step g)."""

from pika.adapters.blocking_connection import BlockingChannel

from grow8_common.config import get_settings


def declare_exchange(channel: BlockingChannel) -> str:
    """Declare the durable topic exchange all events go through; returns its name."""
    name = get_settings().rabbitmq_exchange
    channel.exchange_declare(exchange=name, exchange_type="topic", durable=True)
    return name
