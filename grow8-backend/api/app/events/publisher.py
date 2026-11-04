"""The only place the API talks to RabbitMQ. Call publish() only AFTER the DB commit.

Kept behind this module so it can later be swapped for a transactional outbox.
"""

import logging
from functools import lru_cache
from typing import Annotated, Protocol

import pika
from fastapi import Depends
from grow8_common.events import EventEnvelope, EventType
from grow8_common.messaging import connect
from grow8_common.messaging.topology import declare_exchange
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class EventPublisher(Protocol):
    def publish(
        self, payload: BaseModel, event_type: EventType, correlation_id: str | None
    ) -> None: ...


class RabbitMQPublisher:
    def publish(
        self, payload: BaseModel, event_type: EventType, correlation_id: str | None
    ) -> None:
        """Never raises: the state is already committed, so a failed publish is
        logged loudly instead of failing the request."""
        envelope = EventEnvelope.build(payload, event_type, correlation_id)
        try:
            self._send(envelope)
        except Exception:
            logger.exception(
                "EVENT PUBLISH FAILED after retries: event_id=%s event_type=%s correlation_id=%s",
                envelope.event_id,
                envelope.event_type,
                envelope.correlation_id,
            )
            return
        logger.info(
            "published event_id=%s routing_key=%s", envelope.event_id, envelope.routing_key
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4), reraise=True)
    def _send(self, envelope: EventEnvelope) -> None:
        connection = connect(socket_timeout=5)
        try:
            channel = connection.channel()
            channel.confirm_delivery()
            exchange = declare_exchange(channel)
            channel.basic_publish(
                exchange=exchange,
                routing_key=envelope.routing_key,
                body=envelope.model_dump_json().encode(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    message_id=str(envelope.event_id),
                    correlation_id=envelope.correlation_id,
                    type=envelope.event_type.value,
                ),
            )
        finally:
            connection.close()


@lru_cache
def get_publisher() -> EventPublisher:
    return RabbitMQPublisher()


Publisher = Annotated[EventPublisher, Depends(get_publisher)]
