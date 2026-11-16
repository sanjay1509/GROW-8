# ADR 0010: Retry failed handlers with a delay before dead-lettering

- **Status:** accepted
- **Date:** 2026-11-15

## Context

Every consumer service handled any failure the same way: reject the message without requeue, and RabbitMQ moved it to `<queue>.dlq`. That is right for a message that can never succeed (unreadable JSON, unknown event type, invalid payload). It is wrong for a *temporary* failure. If MySQL restarts or a connection drops while a handler runs, the event is parked although it would succeed a few seconds later. The user misses a notification until someone notices the DLQ and replays it by hand.

Requeueing at once (`requeue=True`) is no fix: the message comes straight back, fails again in a tight loop and blocks the queue. Sleeping in the handler blocks the consumer and every message behind it.

## Decision

1. **Two kinds of failure.** `process()` now returns `RETRY` when the handler raises, and `DEAD_LETTER` only for a bad message. Bad messages still go to the DLQ at once.
2. **Delays are scheduled by RabbitMQ, not by the consumer.** Each service has three retry queues with no consumer: `grow8.<service>.retry.5s`, `.retry.30s` and `.retry.120s`.
   - Each has a queue TTL (`x-message-ttl`). When a message expires, RabbitMQ dead-letters it through the default exchange back to `grow8.<service>`, where it is handled again.
   - There is one queue per delay because RabbitMQ only expires messages at the head of a queue. A 5 s wait queued behind a 120 s one would wait 120 s.
   - The delay is in the queue name, so changing a delay creates a new queue instead of failing on a redeclare with different arguments.
3. **Counting.** The consumer counts retries in its own header, `x-grow8-retries`, which `x-death` doesn't replace because it records TTL expiries and rejections differently across RabbitMQ versions. A failed handler sends the message to retry queue N (where N is the count so far). After the 3rd retry fails (about 2.5 minutes after the first attempt), it is rejected and goes to the DLQ as before.
4. **Never lose, at worst duplicate.** The consumer channel has publisher confirms on. `settle()` publishes the copy to the retry queue, waits for RabbitMQ to confirm it, and only then acks the original. If the publish fails, the original stays unacked and is redelivered. A crash between the publish and the ack produces a duplicate, which idempotent handlers already absorb (`UNIQUE (event_id, user_id)`). The copy keeps `message_id`, `correlation_id`, `type` and any other headers.
5. **Errors must reach the consumer.** `DbNotifier` used `INSERT IGNORE` for idempotency. In MySQL, `IGNORE` also downgrades other errors to warnings: a notification for a user who doesn't exist (FK violation) was silently dropped and the event reported as processed, so neither retrying nor the DLQ ever saw it. It now uses `INSERT … ON DUPLICATE KEY UPDATE event_id = event_id`, which skips only the duplicate `(event_id, user_id)` and lets every other error raise. This amends [ADR 0003](0003-persisted-notifications.md) decision 3.
6. **Other consumers keep working while one message waits.** The main queue doesn't stop while a message waits in a retry queue, so one failing event doesn't hold up the others. Ordering between events was never guaranteed, and no handler relies on it.

## Consequences

- Six new durable queues in the RabbitMQ UI (three per consumer service). They are declared on startup like the others; admin_service gets its own once it has handlers. No API change.
- A message that fails for good now takes about 2.5 minutes to reach the DLQ instead of arriving at once. Its log shows each retry (`retry 1/3 of message_id=… in 5s`), then `dead-lettering … after 3 retries`.
- **Replaying from the DLQ:** a message moved back from the DLQ keeps its retry count, so if it fails again it returns to the DLQ at once instead of retrying for another 2.5 minutes. Replay after fixing the cause.
- A notification for a user deleted between the event and its handling now fails its FK, is retried, and lands in the DLQ instead of vanishing silently. That's rare, and visible on purpose.
- A handler bug that always raises now produces 3 extra attempts per event. They are cheap, and they show up in the logs.
- Unchanged: an event lost at publish time (RabbitMQ down when the API publishes) still needs the transactional outbox, which remains future work.
