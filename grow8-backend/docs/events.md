# GROW8 events

All events go through the durable topic exchange `grow8.events` (`RABBITMQ_EXCHANGE`). Types and payload schemas live in `shared/grow8_common/events/`; never hand-write event JSON elsewhere.

## Envelope

```json
{
  "event_id": "uuid4",
  "event_type": "OPPORTUNITY_CREATED",
  "version": 1,
  "occurred_at": "2026-10-16T06:16:20.915219Z",
  "correlation_id": "X-Request-ID of the API call",
  "payload": { }
}
```

- Routing key = event type lower-cased with dots (`OPPORTUNITY_CREATED` → `opportunity.created`).
- AMQP properties: `content_type=application/json`, persistent, `message_id=event_id`, `type=event_type`, `correlation_id`.
- Published by `api/app/events/publisher.py` only **after** the DB commit, with 3 attempts and backoff. A publish that still fails is logged as `EVENT PUBLISH FAILED` and the request still succeeds (the state is committed). Transactional outbox = future work.

## Queues and failure handling

Each consumer service owns one durable queue, declared on startup by `grow8_common.messaging.run_consumer()` (see `shared/grow8_common/messaging/topology.py`):

| Queue | Bound to (routing keys) | Dead-letter queue |
| --- | --- | --- |
| `grow8.contributor_service` | `opportunity.created` | `grow8.contributor_service.dlq` |
| `grow8.creator_service` | `opportunity.created` | `grow8.creator_service.dlq` |

- A message is **acked only after its handler returns**, so a crash mid-handler means RabbitMQ redelivers it.
- A message that can't be processed (unreadable JSON, no handler, payload fails its schema, handler raises) is **rejected without requeue** and moves to the service's `.dlq` via the `grow8.events.dlx` exchange. Inspect or replay it from the RabbitMQ UI (Queues → `…dlq` → Get messages / Move messages).
- Queues are durable and messages persistent, so an event published while a consumer is down waits in its queue and is processed when the consumer starts.
- Delivery is at-least-once: every handler must be safe to run twice for the same `event_id`.

## Implemented

### `OPPORTUNITY_CREATED` (v1)

- **When:** a creator publishes a draft (`POST /api/v1/opportunities/{id}/publish`), i.e. when it becomes visible to contributors.
- **Consumed by:** both services below, each from its own queue. One event, two independent notifications, both with the same `event_id`.
  - **contributor_service** → `app/handlers/opportunity_created.py`. It re-checks that the opportunity is still `open`, finds active contributors who have at least one of the opportunity's skills (all active contributors if it lists none; query in `grow8_common/queries/matching.py`), and notifies each one: `grow8_common.notifications.DbNotifier` adds one `notification` row per contributor (type `opportunity_created`, title `New opportunity: <title>`, linked to the opportunity), and the service commits before the message is acked ([ADR 0003](adr/0003-persisted-notifications.md)). Those rows are its only writes. `UNIQUE (event_id, user_id)` + `INSERT IGNORE` means a redelivered event adds nothing.
  - **creator_service** → `app/handlers/opportunity_created.py`. It re-checks that the opportunity is still `open`, looks up the organization's owner (`grow8_common/queries/organizations.py`; skipped if their account is inactive), and stores one `opportunity_published` notification for them: `Your opportunity is live: <title>`. Same commit-then-ack and redelivery rules as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `opportunity_id` | int | |
| `organization_id` | int | |
| `title` | string | |
| `category_code` | string | `knowledge` \| `community` |
| `application_deadline` | ISO-8601 UTC | |
| `skill_codes` | string[] | Sorted by code. |

### Seeing it end to end (Check-in I demo)

1. `make up`, then `docker compose logs -f contributor_service creator_service` in a second terminal.
2. In Swagger (<http://localhost:8000/docs>) log in as `yyc.events@grow8.dev` / `Grow8Dev!2026` and **Authorize** with the token.
3. `POST /api/v1/opportunities/15/publish` (seeded draft "Volunteer coordinator for spring market", skills `customer-service`, `event-setup`).
4. The contributor_service log shows `notified 1 contributor(s): [6]` (Jordan Lee has both skills), the creator_service log shows `notified creator user_id=4` (Sofia Martinez owns YYC Neighbourhood Events), and each shows `processed event_id=… correlation_id=<the request's X-Request-ID>`.
   `make mysql`, then `SELECT user_id, title, message, read_at FROM notification;` shows two unread notifications: Jordan's (`opportunity_created`) and Sofia's (`opportunity_published`).
5. Optional, to show durability: `docker compose stop contributor_service`, publish another draft, watch `grow8.contributor_service` hold 1 message in the RabbitMQ UI (<http://localhost:15672>), then `docker compose start contributor_service` and see it processed.

`make reset-db` puts draft 15 back if you want to repeat the demo.

## Not yet implemented

`APPLICATION_SUBMITTED`, `APPLICATION_DECIDED`, `WORK_SUBMITTED`, `WORK_VERIFIED`, `WORK_REJECTED`, `FEEDBACK_SUBMITTED`, `FEEDBACK_APPROVED`, `FEEDBACK_REJECTED` exist in `EventType` but have no payload schema or producer yet. Queues, bindings and dead-lettering per service come with the consumers.
