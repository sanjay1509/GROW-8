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

## Implemented

### `OPPORTUNITY_CREATED` (v1)

- **When:** a creator publishes a draft (`POST /api/v1/opportunities/{id}/publish`), i.e. when it becomes visible to contributors.
- **Consumed by:** contributor_service (handler not built yet; until then the event is routed nowhere and dropped).
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `opportunity_id` | int | |
| `organization_id` | int | |
| `title` | string | |
| `category_code` | string | `knowledge` \| `community` |
| `application_deadline` | ISO-8601 UTC | |
| `skill_codes` | string[] | Sorted by code. |

## Not yet implemented

`APPLICATION_SUBMITTED`, `APPLICATION_DECIDED`, `WORK_SUBMITTED`, `WORK_VERIFIED`, `WORK_REJECTED`, `FEEDBACK_SUBMITTED`, `FEEDBACK_APPROVED`, `FEEDBACK_REJECTED` exist in `EventType` but have no payload schema or producer yet. Queues, bindings and dead-lettering per service come with the consumers.
