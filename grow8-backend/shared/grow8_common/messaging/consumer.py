"""Shared consume loop for the three consumer services.

`process()` decides what happens to one message and does no I/O of its own, so it can
be unit-tested without RabbitMQ. `run_consumer()` wires it to a real queue.

Delivery rules:
- A message is acknowledged only after its handler returns.
- Anything that cannot be processed (bad JSON, unknown event type, invalid payload, a
  handler error) is rejected without requeue, so RabbitMQ moves it to the service's
  dead-letter queue (`<queue>.dlq`) where it can be inspected and replayed from the UI.
- Delivery is at-least-once, so handlers must be safe to run twice for the same event.
"""

import logging
import time
from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Any

from pika.exceptions import AMQPError
from pydantic import ValidationError

from grow8_common.events import PAYLOAD_SCHEMAS, EventEnvelope, EventType
from grow8_common.messaging.connection import connect_with_retry
from grow8_common.messaging.topology import declare_service_queue

logger = logging.getLogger(__name__)

# A handler receives the envelope and its payload, already validated against the
# payload schema registered for that event type in grow8_common.events.payloads.
Handler = Callable[[EventEnvelope, Any], None]


class Outcome(StrEnum):
    ACK = "ack"
    DEAD_LETTER = "dead_letter"


def process(body: bytes, handlers: Mapping[EventType, Handler]) -> Outcome:
    """Decode one message, run its handler and say whether to ack or dead-letter it."""
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
            "dead-lettering event_id=%s event_type=%s correlation_id=%s: handler failed",
            envelope.event_id,
            envelope.event_type,
            envelope.correlation_id,
        )
        return Outcome.DEAD_LETTER

    logger.info(
        "processed event_id=%s event_type=%s correlation_id=%s",
        envelope.event_id,
        envelope.event_type,
        envelope.correlation_id,
    )
    return Outcome.ACK


def run_consumer(
    service: str, handlers: Mapping[EventType, Handler], prefetch_count: int = 10
) -> None:
    """Consume `service`'s queue forever, reconnecting with backoff if RabbitMQ goes away."""
    routing_keys = [event_type.routing_key for event_type in handlers]
    while True:
        connection = connect_with_retry()
        try:
            channel = connection.channel()
            queue = declare_service_queue(channel, service, routing_keys)
            channel.basic_qos(prefetch_count=prefetch_count)

            def on_message(ch: Any, method: Any, _properties: Any, body: bytes) -> None:
                if process(body, handlers) is Outcome.ACK:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(queue=queue, on_message_callback=on_message)
            logger.info("consuming queue=%s routing_keys=%s", queue, routing_keys)
            channel.start_consuming()
        except AMQPError as exc:
            logger.warning("rabbitmq connection lost (%s); reconnecting", type(exc).__name__)
            time.sleep(2)
        finally:
            if connection.is_open:
                connection.close()
