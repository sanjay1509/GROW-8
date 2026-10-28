# ADR 0003: Persist notifications in a `notification` table

- **Status:** accepted
- **Date:** 2026-10-27

## Context

The event catalog has several "notify the user" behaviours. The first one, `OPPORTUNITY_CREATED`, already reaches contributor_service and finds the matching contributors. But a notification there is only a log line (`LogNotifier`), so no user can ever see it. The 17-entity schema from the ENSF 608 proposal has no place to store notifications, and the frontend needs something to show behind its navbar bell.

## Decision

1. **Add an 18th table, `notification`.** It holds one row per user per event: `user_id`, `event_id`, `notification_type`, `title`, `message`, an optional `opportunity_id` link, and `read_at` (`NULL` means unread).
2. **Consumers write it and the API reads it.** The services insert through a `DbNotifier` (in `grow8_common`) that implements the existing `Notifier` interface, so the handlers don't change. The API only reads rows and sets `read_at`.
3. **Idempotency comes from the schema.** `UNIQUE (event_id, user_id)` plus `INSERT IGNORE` makes a redelivered event a no-op, as CLAUDE.md's "consumers are idempotent" rule requires. The service commits before acking.
4. **`title` and `message` are stored as written, not rebuilt from the opportunity.** A notification records what the user was told at that time, like a sent email. This is not a functional dependency on `opportunity`, so the table stays in BCNF: every non-key attribute depends on `notification_id`, and the only other candidate key is `(event_id, user_id)`.
5. **Deleting things:** deleting a user deletes their notifications (`ON DELETE CASCADE`). Deleting an opportunity keeps them and sets `opportunity_id` to `NULL` (`ON DELETE SET NULL`).
6. **`notification_type` is an ENUM** that gains one value per event that notifies users.
7. **The browser polls.** It fetches the unread count over REST. Real-time push (SSE fed by a `NOTIFICATION_CREATED` event) is future work, and nothing in this design blocks it.

## Consequences

- After pulling this change, each developer must run `make reset-db` (wipes local data).
- The ENSF 608 schema documentation (ER diagram, relationship list, FD/BCNF analysis) must add `notification` as an entity that is not in the original proposal.
- Rows are never cleaned up automatically. At this project's scale that's fine; a retention job is future work.
