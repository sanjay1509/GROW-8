# ADR 0004: Only draft opportunities can be deleted

- **Status:** accepted
- **Date:** 2026-11-15

## Context

`DELETE /opportunities/{id}` was added for the creator's My Opportunities page. It deleted an opportunity owned by the caller in **any** status. That clashes with the rest of the design:

- [ADR 0001](0001-opportunity-draft-and-publish.md) gives published opportunities a lifecycle (`open` → `closed` / `cancelled`) and forbids editing them so applicants never see terms change under them. Making one disappear is a stronger change than editing it.
- Publishing emits `OPPORTUNITY_CREATED`, and contributors get a notification that links to the opportunity. After a delete, that link leads to a 404 (the notification keeps its text but `opportunity_id` becomes `NULL`, see [ADR 0003](0003-persisted-notifications.md)).
- `application.opportunity_id` references `opportunity` without `ON DELETE`. Once applications exist, deleting a published opportunity fails on the foreign key and the API returns an unhandled 500.

## Decision

1. **Only drafts can be deleted.** A draft has never been visible to anyone but its owner, so removing it affects no one else.
2. A non-draft returns **409 `OPPORTUNITY_NOT_DRAFT`**, the same code `PATCH` and `publish` use for the same reason.
3. Ownership is checked the same way as for editing: someone else's draft → 404 (drafts are invisible to others), someone else's published opportunity → 403 `NOT_OPPORTUNITY_OWNER`.
4. We do **not** add `ON DELETE CASCADE` to `application` (or later `work_submission`, `feedback`). Those rows are the record of real work, verified hours and ratings, and must not vanish because a creator removed a listing.
5. Taking a published opportunity down will be done by **closing or cancelling** it (status change plus an event), not by deleting it. Those endpoints are future work.

## Consequences

- The frontend shows the Delete button only on drafts.
- Until close/cancel exists, a creator who published by mistake cannot take the opportunity down themselves; an admin or a direct database change is needed.
- Deleting a draft cascades only to its `opportunity_skill` rows. Drafts cannot have applications (the `application_closed` trigger in `001_schema.sql` rejects applications to anything not `open`, and nothing moves an opportunity back to `draft`), so the foreign-key failure above cannot happen.
- Covered by `test_owner_can_delete_a_draft`, `test_published_opportunity_cannot_be_deleted` and `test_only_the_owner_can_delete` in `api/tests/integration/test_opportunities.py`.
