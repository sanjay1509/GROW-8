# ADR 0009: Tell the creator when an applicant withdraws

- **Status:** accepted
- **Date:** 2026-11-15
- **Amends:** [ADR 0006](0006-application-lifecycle.md) decision 7 ("withdrawing publishes nothing")

## Context

ADR 0006 published events for applying and deciding, but not for withdrawing: the event catalog had no withdrawal event, and the creator could see the new status in the applications list. In practice the creator has no reason to reopen that list. If an accepted contributor withdraws, the creator expects them to show up, and doesn't know a place has opened. Every other change to an application already reaches the other party as a notification.

## Decision

1. **New event `APPLICATION_WITHDRAWN` (v1)**, published by the API after a successful withdrawal is committed (same commit-then-publish rule and publisher as the other events). A refused withdrawal (409) publishes nothing.
2. **Payload:** `application_id`, `opportunity_id`, `organization_id`, `opportunity_title`, `contributor_id`, `contributor_name` and `previous_status` (`pending` | `accepted`).
   - `previous_status` is in the event because `withdrawn` is final: once committed, the database no longer says what the application was, and that's what the creator cares about.
   - `organization_id` and `contributor_name` are included, as in `APPLICATION_SUBMITTED`, so the consumer doesn't need extra queries for them.
3. **Consumer: creator_service** (it already handles `APPLICATION_SUBMITTED`, the other "an applicant did something" event). It notifies the organization's owner once, skipped if the owner's account is inactive, with notification type `application_withdrawn`:
   - title `Application withdrawn: <opportunity title>`
   - was pending: `<name> withdrew their application before you decided on it.`
   - was accepted: `<name> withdrew after being accepted, so their place is open again.`
4. **Both pending and accepted withdrawals notify.** A pending withdrawal also matters: it removes an application the creator might be about to review and frees a place.
5. **The contributor gets no notification.** They took the action and saw the result in the response.

## Consequences

- `notification.notification_type` gains `application_withdrawn`. This is a schema change. Either run `make reset-db` (wipes local data), or keep your data with the equivalent `ALTER TABLE notification MODIFY notification_type ENUM('opportunity_created', 'opportunity_published', 'application_submitted', 'application_decided', 'application_withdrawn') NOT NULL;`. The ENSF 608 data dictionary lists the new value.
- New binding: `grow8.creator_service` ← `application.withdrawn`, declared when the service starts. Restart creator_service after pulling.
- `POST /applications/{id}/withdraw` now takes the publisher, like apply and decide. The response is unchanged.
- The event catalog in `docs/events.md` and the README gains a row.
