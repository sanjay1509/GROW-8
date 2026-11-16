"""Shared consume loop for the three consumer services (ADR 0010).

`process()` decides what happens to one message and does no I/O of its own, and
`settle()` carries that decision out on a channel, so both can be unit-tested without
RabbitMQ. `run_consumer()` wires them to a real queue.

Delivery rules:
- A message is acknowledged only after its handler returns.
- A **bad message** (bad JSON, unknown event type, invalid payload) can never succeed,
  so it is rejected without requeue and RabbitMQ moves it to the service's dead-letter
  queue (`<queue>.dlq`) at once.
- A **handler error** may be temporary (e.g. MySQL restarting), so the message is
  retried after 5 s, 30 s and 120 s (`RETRY_DELAYS_SECONDS`) through the service's
  retry queues. If the last retry fails too, it goes to the dead-letter queue.
- Messages in the dead-letter queue can be inspected and replayed from the RabbitMQ UI.
- Delivery is at-least-once, so handlers must be safe to run twice for the same event.
"""

import logging
import time
from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Any, Protocol

import pika
from pika.exceptions import AMQPError
from pydantic import ValidationError

from grow8_common.events import PAYLOAD_SCHEMAS, EventEnvelope, EventType
from grow8_common.messaging.connection import connect_with_retry
from grow8_common.messaging.topology import (
    RETRY_DELAYS_SECONDS,
    declare_service_queue,
    retry_queue_name,
)

logger = logging.getLogger(__name__)

# Our own count of how many times a message has been sent back for a retry.
RETRY_HEADER = "x-grow8-retries"

# A handler receives the envelope and its payload, already validated against the
# payload schema registered for that event type in grow8_common.events.payloads.
Handler = Callable[[EventEnvelope, Any], None]


class Outcome(StrEnum):
    ACK = "ack"
    RETRY = "retry"  # the handler failed; it may work later
    DEAD_LETTER = "dead_letter"  # the message itself is bad; it never will


def process(body: bytes, handlers: Mapping[EventType, Handler]) -> Outcome:
    """Decode one message, run its handler and say whether to ack, retry or
    dead-letter it."""
    try:
        envelope = EventEnvelope.model_validate_json(body)
    except ValidationError as exc:
        logger.error("dead-lettering unreadable message: %s", exc.errors()[:3])
        return Outcome.DEAD_LETTER

    handler = handlers.get(envelope.event_type)
    schema = PAYLOAD_SCHEMAS.get(envelope.event_type)
    if handler is None or schema is None:
        logger.error(
            "dead-lettering event_id=%s: no handler or payload schema for %s",
            envelope.event_id,
            envelope.event_type,
        )
        return Outcome.DEAD_LETTER

    try:
        payload = schema.model_validate(envelope.payload)
    except ValidationError as exc:
        logger.error(
            "dead-lettering event_id=%s: invalid %s payload: %s",
            envelope.event_id,
            envelope.event_type,
            exc.errors()[:3],
        )
        return Outcome.DEAD_LETTER

    try:
        handler(envelope, payload)
    except Exception:
        logger.exception(
            "handler failed for event_id=%s event_type=%s correlation_id=%s",
            envelope.event_id,
            envelope.event_type,
            envelope.correlation_id,
        )
        return Outcome.RETRY

    logger.info(
        "processed event_id=%s event_type=%s correlation_id=%s",
        envelope.event_id,
        envelope.event_type,
        envelope.correlation_id,
    )
    return Outcome.ACK


class Channel(Protocol):
    """The part of pika's BlockingChannel that settle() uses."""

    def basic_ack(self, delivery_tag: int) -> None: ...
    def basic_nack(self, delivery_tag: int, requeue: bool) -> None: ...
    def basic_publish(
        self, exchange: str, routing_key: str, body: bytes, properties: pika.BasicProperties
    ) -> None: ...


def retries_so_far(properties: pika.BasicProperties) -> int:
    """How many retries this message has already had (0 for a new one)."""
    value = (properties.headers or {}).get(RETRY_HEADER, 0)
    return value if isinstance(value, int) and value >= 0 else 0


def settle(
    channel: Channel,
    delivery_tag: int,
    properties: pika.BasicProperties,
    body: bytes,
    queue: str,
    outcome: Outcome,
) -> None:
    """Ack, schedule a retry, or dead-letter one delivery according to `outcome`.

    A retry publishes a copy to the next retry queue and only then acks the original.
    The channel has publisher confirms on, so basic_publish returns once RabbitMQ has
    the copy; if it raises, the original stays unacked and is redelivered (a duplicate
    at worst, which idempotent handlers absorb, never a lost message).
    """
    if outcome is Outcome.ACK:
        channel.basic_ack(delivery_tag=delivery_tag)
        return

    retries = retries_so_far(properties)
    if outcome is Outcome.RETRY and retries < len(RETRY_DELAYS_SECONDS):
        delay = RETRY_DELAYS_SECONDS[retries]
        channel.basic_publish(
            exchange="",  # default exchange: routing key = queue name
            routing_key=retry_queue_name(queue, delay),
            body=body,
            properties=pika.BasicProperties(
                content_type=properties.content_type,
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=properties.message_id,
                correlation_id=properties.correlation_id,
                type=properties.type,
                headers={**(properties.headers or {}), RETRY_HEADER: retries + 1},
            ),
        )
        channel.basic_ack(delivery_tag=delivery_tag)
        logger.warning(
            "retry %d/%d of message_id=%s in %ds",
            retries + 1,
            len(RETRY_DELAYS_SECONDS),
            properties.message_id,
            delay,
        )
        return

    if outcome is Outcome.RETRY:
        logger.error(
            "dead-lettering message_id=%s: handler still failing after %d retries",
            properties.message_id,
            retries,
        )
    channel.basic_nack(delivery_tag=delivery_tag, requeue=False)


def run_consumer(
    service: str, handlers: Mapping[EventType, Handler], prefetch_count: int = 10
) -> None:
    """Consume `service`'s queue forever, reconnecting with backoff if RabbitMQ goes away."""
    routing_keys = [event_type.routing_key for event_type in handlers]
    while True:
        connection = connect_with_retry()
        try:
            channel = connection.channel()
            channel.confirm_delivery()  # retry copies are confirmed before the ack
            queue = declare_service_queue(channel, service, routing_keys)
            channel.basic_qos(prefetch_count=prefetch_count)

            def on_message(
                ch: Any, method: Any, properties: Any, body: bytes, queue: str = queue
            ) -> None:
                outcome = process(body, handlers)
                settle(ch, method.delivery_tag, properties, body, queue, outcome)

            channel.basic_consume(queue=queue, on_message_callback=on_message)
            logger.info("consuming queue=%s routing_keys=%s", queue, routing_keys)
            channel.start_consuming()
        except AMQPError as exc:
            logger.warning("rabbitmq connection lost (%s); reconnecting", type(exc).__name__)
            time.sleep(2)
        finally:
            if connection.is_open:
                connection.close()
