"""grow8_common.messaging.settle(): what happens on the channel for each outcome
(ADR 0010). A recording fake stands in for pika's channel."""

from dataclasses import dataclass, field

import pika
import pytest
from grow8_common.messaging import RETRY_HEADER, Outcome, retries_so_far, settle
from grow8_common.messaging.topology import RETRY_DELAYS_SECONDS

QUEUE = "grow8.contributor_service"
BODY = b'{"event_id": "..."}'


@dataclass
class FakeChannel:
    calls: list[tuple] = field(default_factory=list)
    publish_error: Exception | None = None

    def basic_ack(self, delivery_tag: int) -> None:
        self.calls.append(("ack", delivery_tag))

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        self.calls.append(("nack", delivery_tag, requeue))

    def basic_publish(self, exchange, routing_key, body, properties) -> None:
        if self.publish_error:
            raise self.publish_error
        self.calls.append(("publish", exchange, routing_key, body, properties))


def _props(retries: int | None = None, **headers) -> pika.BasicProperties:
    if retries is not None:
        headers[RETRY_HEADER] = retries
    return pika.BasicProperties(
        content_type="application/json",
        message_id="evt-1",
        correlation_id="req-1",
        type="OPPORTUNITY_CREATED",
        headers=headers or None,
    )


def _settle(outcome: Outcome, properties: pika.BasicProperties) -> FakeChannel:
    channel = FakeChannel()
    settle(channel, 7, properties, BODY, QUEUE, outcome)
    return channel


def test_success_is_acked() -> None:
    assert _settle(Outcome.ACK, _props()).calls == [("ack", 7)]


def test_bad_message_is_dead_lettered_at_once() -> None:
    assert _settle(Outcome.DEAD_LETTER, _props()).calls == [("nack", 7, False)]


def test_first_failure_waits_in_the_first_retry_queue_then_acks() -> None:
    channel = _settle(Outcome.RETRY, _props(trace="x"))

    (kind, exchange, routing_key, body, properties), ack = channel.calls
    assert kind == "publish"
    assert exchange == ""
    assert routing_key == "grow8.contributor_service.retry.5s"
    assert body == BODY
    assert properties.headers == {"trace": "x", RETRY_HEADER: 1}  # other headers kept
    assert properties.message_id == "evt-1"
    assert properties.correlation_id == "req-1"
    assert properties.type == "OPPORTUNITY_CREATED"
    assert properties.delivery_mode == pika.DeliveryMode.Persistent.value
    assert ack == ("ack", 7)  # only after the copy was published


@pytest.mark.parametrize(
    ("retries", "queue"),
    [
        (1, "grow8.contributor_service.retry.30s"),
        (2, "grow8.contributor_service.retry.120s"),
    ],
)
def test_each_retry_waits_longer(retries: int, queue: str) -> None:
    channel = _settle(Outcome.RETRY, _props(retries))

    assert channel.calls[0][2] == queue
    assert channel.calls[0][4].headers[RETRY_HEADER] == retries + 1


def test_dead_lettered_once_the_retries_are_used_up() -> None:
    channel = _settle(Outcome.RETRY, _props(len(RETRY_DELAYS_SECONDS)))

    assert channel.calls == [("nack", 7, False)]


def test_failed_retry_publish_leaves_the_message_unacked() -> None:
    channel = FakeChannel(publish_error=RuntimeError("connection lost"))

    with pytest.raises(RuntimeError):
        settle(channel, 7, _props(), BODY, QUEUE, Outcome.RETRY)
    assert channel.calls == []  # neither acked nor nacked: RabbitMQ redelivers it


@pytest.mark.parametrize(
    ("headers", "expected"),
    [(None, 0), ({}, 0), ({RETRY_HEADER: 2}, 2), ({RETRY_HEADER: "2"}, 0), ({RETRY_HEADER: -1}, 0)],
)
def test_retries_so_far_trusts_only_a_non_negative_int(headers, expected) -> None:
    assert retries_so_far(pika.BasicProperties(headers=headers)) == expected


def test_delays_grow() -> None:
    assert list(RETRY_DELAYS_SECONDS) == sorted(RETRY_DELAYS_SECONDS)
