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

| Queue | Bound to (routing keys) | Retry queues | Dead-letter queue |
| --- | --- | --- | --- |
| `grow8.contributor_service` | `opportunity.created`, `application.decided`, `opportunity.cancelled`, `work.verified`, `work.rejected`, `feedback.approved`, `feedback.rejected`, `opportunity.taken.down`, `report.dismissed` | `grow8.contributor_service.retry.{5s,30s,120s}` | `grow8.contributor_service.dlq` |
| `grow8.creator_service` | `opportunity.created`, `application.submitted`, `application.withdrawn`, `work.submitted`, `feedback.approved`, `feedback.rejected`, `opportunity.taken.down` | `grow8.creator_service.retry.{5s,30s,120s}` | `grow8.creator_service.dlq` |
| `grow8.admin_service` | `feedback.submitted`, `opportunity.reported` | `grow8.admin_service.retry.{5s,30s,120s}` | `grow8.admin_service.dlq` |

- A message is **acked only after its handler returns**, so a crash mid-handler means RabbitMQ redelivers it.
- A **bad message** (unreadable JSON, no handler, payload fails its schema) can never succeed, so it is **rejected without requeue** and moves to the service's `.dlq` via the `grow8.events.dlx` exchange at once.
- A **handler error** may be temporary (e.g. MySQL restarting), so the message is **retried after 5 s, 30 s and 120 s** ([ADR 0010](adr/0010-delayed-retry-before-dead-letter.md)). It waits in `grow8.<service>.retry.5s` / `.30s` / `.120s`, queues with a TTL and no consumer, whose expired messages flow back to the main queue. The `x-grow8-retries` header counts the retries. If the 3rd retry fails too (about 2.5 min after the first attempt), the message goes to the `.dlq`. Logs: `retry 1/3 of message_id=… in 5s`, then `dead-lettering … after 3 retries`.
- Inspect or replay a dead-lettered message from the RabbitMQ UI (Queues → `…dlq` → Get messages / Move messages). A replayed message keeps its retry count, so replay after fixing the cause: if it fails again it returns to the DLQ at once.
- Queues are durable and messages persistent, so an event published while a consumer is down waits in its queue and is processed when the consumer starts.
- Delivery is at-least-once: every handler must be safe to run twice for the same `event_id`.

## Implemented

### `OPPORTUNITY_CREATED` (v1)

- **When:** a creator publishes a draft (`POST /api/v1/opportunities/{id}/publish`), i.e. when it becomes visible to contributors.
- **Consumed by:** both services below, each from its own queue. One event, two independent notifications, both with the same `event_id`.
  - **contributor_service** → `app/handlers/opportunity_created.py`. It re-checks that the opportunity is still `open`, finds active contributors who have at least one of the opportunity's skills (all active contributors if it lists none; query in `grow8_common/queries/matching.py`), and notifies each one: `grow8_common.notifications.DbNotifier` adds one `notification` row per contributor (type `opportunity_created`, title `New opportunity: <title>`, linked to the opportunity), and the service commits before the message is acked ([ADR 0003](adr/0003-persisted-notifications.md)). Those rows are its only writes. `UNIQUE (event_id, user_id)` + a no-op `ON DUPLICATE KEY UPDATE` means a redelivered event adds nothing; any other insert error (e.g. an unknown user) raises and is retried.
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

### `APPLICATION_SUBMITTED` (v1)

- **When:** a contributor applies (`POST /api/v1/opportunities/{id}/applications`), after the application is committed ([ADR 0006](adr/0006-application-lifecycle.md)).
- **Consumed by:** **creator_service** → `app/handlers/application_submitted.py`. It looks up the organization's owner (skipped if their account is inactive) and stores one `application_submitted` notification: `New application: <opportunity title>`, message `<contributor name> applied. …`, linked to the opportunity. Commit-then-ack and duplicate-safe insert as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `application_id` | int | |
| `opportunity_id` | int | |
| `organization_id` | int | Used to find whom to notify. |
| `opportunity_title` | string | As it was when the contributor applied. |
| `contributor_id` | int | |
| `contributor_name` | string | |

### `APPLICATION_DECIDED` (v1)

- **When:** the owning creator accepts or rejects a pending application (`POST /api/v1/applications/{id}/decision`). Each application is decided once, so this is sent at most once per application.
- **Consumed by:** **contributor_service** → `app/handlers/application_decided.py`. It stores one `application_decided` notification for the applicant: `You were accepted: <title>` or `Application update: <title>`, linked to the opportunity. The decision is taken from the event, not re-read: it is final.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `application_id` | int | |
| `opportunity_id` | int | |
| `opportunity_title` | string | |
| `contributor_id` | int | Whom to notify. |
| `decision` | string | `accepted` \| `rejected` |

### `APPLICATION_WITHDRAWN` (v1)

- **When:** the applicant withdraws a pending or accepted application (`POST /api/v1/applications/{id}/withdraw`), after the withdrawal is committed ([ADR 0009](adr/0009-application-withdrawn-event.md)). A refused withdrawal (409) sends nothing. `withdrawn` is final, so this is sent at most once per application.
- **Consumed by:** **creator_service** → `app/handlers/application_withdrawn.py`. It looks up the organization's owner (skipped if their account is inactive) and stores one `application_withdrawn` notification: `Application withdrawn: <opportunity title>`, with a message that says whether an accepted place opened up, linked to the opportunity. Commit-then-ack and duplicate-safe insert as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `application_id` | int | |
| `opportunity_id` | int | |
| `organization_id` | int | Used to find whom to notify. |
| `opportunity_title` | string | |
| `contributor_id` | int | |
| `contributor_name` | string | |
| `previous_status` | string | `pending` \| `accepted`: what it was before withdrawal (the database no longer says). |

### `OPPORTUNITY_CANCELLED` (v1)

- **When:** the owning creator cancels an open or closed opportunity (`POST /api/v1/opportunities/{id}/cancel`), after the commit ([ADR 0011](adr/0011-close-and-cancel-opportunities.md)). Cancelled is final, so this is sent at most once per opportunity. Closing sends no event.
- **Consumed by:** **contributor_service** → `app/handlers/opportunity_cancelled.py`. It looks up applicants whose application is still pending or accepted, with active accounts (`grow8_common/queries/applications.py`), and stores one `opportunity_cancelled` notification for each: `Opportunity cancelled: <title>`. The message says a pending application "won't be decided", or that an accepted applicant needn't do anything. Linked to the opportunity. Recipients are looked up at handling time, so anyone who withdrew in between isn't told. Commit-then-ack and duplicate-safe insert as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `opportunity_id` | int | Used to find whom to notify. |
| `organization_id` | int | |
| `title` | string | |

### `WORK_SUBMITTED` (v1)

- **When:** an accepted applicant submits their work (`POST /api/v1/applications/{id}/submission`), after the submission and its attachments are committed ([ADR 0012](adr/0012-work-submission.md)). A refused submission (404/409/413/415/422) sends nothing. There is one submission per application, so this is sent at most once per application.
- **Consumed by:** **creator_service** → `app/handlers/work_submitted.py`. It looks up the organization's owner (skipped if their account is inactive) and stores one `work_submitted` notification: `Work submitted: <opportunity title>`, with a message such as "Alex Chen submitted 6.5 h of work with 2 files for you to verify.", linked to the opportunity. Commit-then-ack and duplicate-safe insert as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `submission_id` | int | |
| `application_id` | int | |
| `opportunity_id` | int | |
| `organization_id` | int | Used to find whom to notify. |
| `opportunity_title` | string | |
| `contributor_id` | int | |
| `contributor_name` | string | |
| `hours_claimed` | string (decimal) | Sent as a JSON string, e.g. `"6.50"`, so no precision is lost. |
| `attachment_count` | int | 0–5. |

### `WORK_VERIFIED` (v1)

- **When:** the owning creator approves submitted work (`POST /api/v1/submissions/{id}/verification` with `decision: "approved"`), after the verification is committed ([ADR 0013](adr/0013-work-verification.md)). A refused verification (404/409/422) sends nothing. Each submission is verified once, so this is sent at most once per submission, and never together with `WORK_REJECTED` for the same one.
- **Consumed by:** **contributor_service** → `app/handlers/work_verified.py`. It stores one `work_verified` notification for the contributor: `Work verified: <title>`, with a message such as "Your work on … was verified (6 h).", linked to the opportunity. The decision is taken from the event, not re-read: it is final. Verified hours and skills need no write, since the views compute them from approved verifications. Commit-then-ack and duplicate-safe insert as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `verification_id` | int | Identifies this approval for good: the rewards handler (#24) can award its points once per verification. |
| `submission_id` | int | |
| `application_id` | int | |
| `opportunity_id` | int | |
| `organization_id` | int | |
| `opportunity_title` | string | |
| `contributor_id` | int | Whom to notify. |
| `verified_hours` | string (decimal) | Sent as a JSON string, e.g. `"6.00"`. At most the hours claimed. |

### `WORK_REJECTED` (v1)

- **When:** the owning creator rejects submitted work (`POST /api/v1/submissions/{id}/verification` with `decision: "rejected"`), after the commit ([ADR 0013](adr/0013-work-verification.md)). Sent at most once per submission.
- **Consumed by:** **contributor_service** → `app/handlers/work_rejected.py`. It stores one `work_rejected` notification for the contributor: `Work not verified: <title>`, quoting the creator's comment (shortened if it doesn't fit the 500-character message; the full comment is on the submission), linked to the opportunity. Commit-then-ack and duplicate-safe insert as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `verification_id` | int | |
| `submission_id` | int | |
| `application_id` | int | |
| `opportunity_id` | int | |
| `organization_id` | int | |
| `opportunity_title` | string | |
| `contributor_id` | int | Whom to notify. |
| `comment` | string | Why the work was rejected (required when rejecting, 1–2000 characters). |

### `FEEDBACK_SUBMITTED` (v1)

- **When:** the applicant or the owning creator leaves feedback on an application whose work has been verified (`POST /api/v1/applications/{id}/feedback`), after the commit ([ADR 0015](adr/0015-feedback-and-admin-review.md)). A refused feedback (404/409/422) sends nothing. One feedback per author per application, so this is sent at most twice per application.
- **Consumed by:** **admin_service** → `app/handlers/feedback_submitted.py`. It looks up every active admin (`grow8_common/queries/users.py`) and stores one `feedback_submitted` notification for each: `Feedback to review: <title>`, or `Discrepancy reported: <title>` when `reports_discrepancy` is set. Linked to the opportunity. Commit-then-ack and duplicate-safe insert as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `feedback_id` | int | |
| `application_id` | int | |
| `opportunity_id` | int | |
| `opportunity_title` | string | |
| `author_user_id` | int | |
| `author_name` | string | |
| `author_role` | string | `contributor` \| `creator` |
| `subject_user_id` | int | Always the other participant. |
| `rating` | int | 1–5. |
| `reports_discrepancy` | bool | |

### `FEEDBACK_APPROVED` (v1)

- **When:** an admin approves feedback (`POST /api/v1/admin/feedback/{id}/review` with `decision: "approved"`), after the commit. Each feedback is reviewed once, so this is sent at most once per feedback, and never together with `FEEDBACK_REJECTED` for the same one.
- **Consumed by:** **creator_service** and **contributor_service** → `app/handlers/feedback_approved.py` in each. Each service notifies only the participant on its own side, so the author and the subject each get exactly one `feedback_approved` notification. The author gets `Your feedback was published: <title>`; the subject gets `New rating: <title>` ("Alex Chen rated you 5/5 for …"). The wording lives in `grow8_common/notifications/feedback.py`, shared by both services. The rating itself needs no write: `v_user_rating` counts approved feedback.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `feedback_id` | int | |
| `application_id` | int | |
| `opportunity_id` | int | |
| `opportunity_title` | string | |
| `author_user_id` | int | |
| `author_name` | string | |
| `author_role` | string | `contributor` \| `creator`: decides which service tells the author and which tells the subject. |
| `subject_user_id` | int | |
| `subject_name` | string | |
| `rating` | int | 1–5. |

### `FEEDBACK_REJECTED` (v1)

- **When:** an admin rejects feedback with a reason (`POST /api/v1/admin/feedback/{id}/review` with `decision: "rejected"`), after the commit. Sent at most once per feedback.
- **Consumed by:** **creator_service** and **contributor_service** → `app/handlers/feedback_rejected.py`. Only the service on the **author's** side acts: it stores one `feedback_rejected` notification, `Your feedback was not published: <title>`, quoting the reason. The other service does nothing. The subject is never told about feedback that doesn't count (ADR 0015 decision 7).
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `feedback_id` | int | |
| `application_id` | int | |
| `opportunity_id` | int | |
| `opportunity_title` | string | |
| `author_user_id` | int | Whom to notify. |
| `author_role` | string | `contributor` \| `creator` |
| `subject_name` | string | Named in the author's message. |
| `reason` | string | Required when rejecting, at most 500 characters. |

### `OPPORTUNITY_REPORTED` (v1)

- **When:** a contributor reports a published opportunity (`POST /api/v1/opportunities/{id}/reports`), after the commit ([ADR 0016](adr/0016-opportunity-reports-and-takedown.md)). A refused report sends nothing. One report per contributor per opportunity.
- **Consumed by:** **admin_service** → `app/handlers/opportunity_reported.py`. It stores one `opportunity_reported` notification for every active admin: `Opportunity reported: <title>`, with the reason in words and how many reports are open on it. The reporter isn't named; admins see who reported in `GET /admin/reports`.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `report_id` | int | |
| `opportunity_id` | int | |
| `opportunity_title` | string | |
| `reason` | string | `misleading_terms` \| `unsafe_conditions` \| `discriminatory` \| `scam_or_spam` \| `other` |
| `open_reports` | int | Pending reports on the opportunity, this one included. |

### `OPPORTUNITY_TAKEN_DOWN` (v1)

- **When:** an admin upholds a report (`POST /api/v1/admin/reports/{id}/review` with `decision: "upheld"`), after the opportunity is cancelled and every pending report on it is upheld in one transaction. An opportunity is taken down at most once (cancelled is final).
- **Consumed by:**
  - **creator_service** → `app/handlers/opportunity_taken_down.py`: one notification for the organization's owner (skipped if inactive), `Opportunity taken down: <title>`, quoting the admin's reason. Who reported is never said.
  - **contributor_service** → `app/handlers/opportunity_taken_down.py`: one notification per pending or accepted applicant (looked up at handling time) and per reporter (from the event). Applicants hear it "won't go ahead", without the reason; reporters get `Thanks for your report: <title>`. A reporter who also applied gets the reporter message only.

  All use `opportunity_taken_down`. Commit-then-ack and duplicate-safe insert as above.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `opportunity_id` | int | |
| `organization_id` | int | Used to find the owner. |
| `title` | string | |
| `reason` | string | What the admin told the creator. |
| `reporter_user_ids` | int[] | Everyone whose report was upheld by this takedown. |

### `REPORT_DISMISSED` (v1)

- **When:** an admin dismisses one report (`decision: "dismissed"`), after the commit. Sent at most once per report.
- **Consumed by:** **contributor_service** → `app/handlers/report_dismissed.py`: one `report_dismissed` notification for the reporter, `Report reviewed: <title>`, with the admin's note if any. Nobody else is told.
- **Payload:**

| Field | Type | Notes |
| --- | --- | --- |
| `report_id` | int | |
| `opportunity_id` | int | |
| `opportunity_title` | string | |
| `reporter_user_id` | int | Whom to notify. |
| `reason` | string \| null | The admin's optional note. |

### Seeing it end to end (Check-in I demo)

1. `make reset-db` (fresh seed: draft 15 back, no notifications; **wipes local data**), then `docker compose logs -f contributor_service creator_service` in a second terminal.
2. In Swagger (<http://localhost:8000/docs>) log in (`POST /api/v1/auth/login`) as `yyc.events@grow8.dev` / `Grow8Dev!2026` and **Authorize** with the token.
3. `POST /api/v1/opportunities/15/publish` (seeded draft "Volunteer coordinator for spring market", skills `customer-service`, `event-setup`).
4. The contributor_service log shows `notified 1 contributor(s): [6]` (Jordan Lee has both skills), the creator_service log shows `notified creator user_id=4` (Sofia Martinez owns YYC Neighbourhood Events), and each shows `processed event_id=… correlation_id=<the request's X-Request-ID>`. Same `event_id` in both: one event, two services.
5. Still authorized as Sofia: `GET /api/v1/notifications` shows "Your opportunity is live: Volunteer coordinator for spring market" (`opportunity_published`, `is_read: false`).
6. Log in as `jordan.lee@grow8.dev` and re-authorize: `GET /api/v1/notifications/unread-count` → `{"unread_count": 1}`; `GET /api/v1/notifications` shows "New opportunity: …" (`opportunity_created`). `PATCH /api/v1/notifications/{notification_id}/read`, then the count is 0.
7. Optional, to show durability: `docker compose stop contributor_service`, publish another draft, watch `grow8.contributor_service` hold 1 message in the RabbitMQ UI (<http://localhost:15672>), then `docker compose start contributor_service` and see it processed. The creator's notification arrived meanwhile: the services don't depend on each other.

`make postman` runs the same flow automatically (folder "4. Notifications"); `make reset-db` puts draft 15 back if you want to repeat the demo.

## Not yet implemented

Every event in `EventType` now has a payload schema, a producer and at least one consumer.
