# ADR 0011: Closing and cancelling published opportunities

- **Status:** accepted
- **Date:** 2026-11-16
- **Completes:** [ADR 0001](0001-opportunity-draft-and-publish.md) ("closing and cancelling will need their own endpoints and events later"). **Amends:** [ADR 0006](0006-application-lifecycle.md) decision 1 (deciding after a cancel).

## Context

The schema has had `closed` and `cancelled` opportunity statuses from the start, and the application trigger already refuses applications to anything not `open`. But nothing could move an opportunity there. A creator who filled their places, or whose event fell through, could only wait for the deadline. Pending applications then stayed pending with no signal to the applicants. Published opportunities can't be deleted ([ADR 0004](0004-only-drafts-can-be-deleted.md)), so closing and cancelling are the only ways to end one.

## Decision

1. **Two actions for the owning creator** (same ownership rules as publishing: someone else's draft → 404, someone else's public opportunity → 403 `NOT_OPPORTUNITY_OWNER`):

   ```text
   draft ──publish──▶ open ──close──▶ closed
                        │                │
                        └────cancel──────┴──▶ cancelled
   ```

2. **Close (`POST /opportunities/{id}/close`):** `open` → `closed`. It means "no more applications", nothing else.
   - New applications get the existing 409 `OPPORTUNITY_NOT_OPEN`, from the service and the trigger alike.
   - Pending applications stay pending and can still be decided (ADR 0006 already allows deciding after the window). There's **no auto-reject**, consistent with ADR 0006.
   - **Nobody is notified.** Applicants learn the outcome when the creator decides.
   - Only an `open` opportunity can be closed; anything else → 409 `OPPORTUNITY_NOT_OPEN`. **Closed is final for now.** Reopening needs its own decision (e.g. about a deadline that has passed).
3. **Cancel (`POST /opportunities/{id}/cancel`):** `open` or `closed` → `cancelled`. It means "this won't happen".
   - **Application statuses are kept.** Rewriting them would misstate what happened: `rejected` implies a judgment and `withdrawn` implies the contributor acted. Clients show "cancelled" from `opportunity.status`, which every application includes. No schema change.
   - **Deciding is refused** afterwards: 409 `OPPORTUNITY_CANCELLED`. Withdrawing is still allowed, since it's harmless.
   - **Refused once work is submitted** for any of its applications (409 `WORK_ALREADY_SUBMITTED`). Verified hours, skills and feedback will depend on that work, as with withdrawal in ADR 0006.
   - A draft → 409 `OPPORTUNITY_NOT_PUBLISHED` (delete it instead). Already cancelled → 409 `OPPORTUNITY_CANCELLED`.
4. **New event `OPPORTUNITY_CANCELLED` (v1)**, published after the commit. The payload is `opportunity_id`, `organization_id`, `title`. **contributor_service** notifies every applicant whose application still holds a place (pending or accepted, active account), with notification type `opportunity_cancelled`. The message differs for pending ("won't be decided") and accepted ("you don't need to do anything").
   - Recipients are looked up when the event is handled, not listed in it. Anyone who withdrew in between isn't told, and statuses can't change after a cancel, so a redelivery finds the same people.
5. **Concurrency:** close and cancel lock the opportunity row (`FOR UPDATE`), and applying already does. A decision takes a shared lock on the opportunity's status (`FOR SHARE`) after locking the application. So a cancel and a decision are serialized: either the decision lands first and the applicant is notified as accepted, or the decision sees `cancelled` and gets 409. Cancel takes no application locks, so the lock order can't deadlock.
6. **Applications received, across opportunities:** `GET /applications/received` lists applications to every opportunity the creator owns, newest first, with `status`, `opportunity_id`, `limit` and `offset`. Before this, a creator dashboard needed one call per opportunity. An `opportunity_id` that isn't the creator's simply matches nothing (no 403/404, so nothing is revealed).

## Consequences

- `notification.notification_type` gains `opportunity_cancelled`: run `make reset-db` (wipes local data), or `ALTER TABLE notification MODIFY notification_type ENUM('opportunity_created', 'opportunity_published', 'application_submitted', 'application_decided', 'application_withdrawn', 'opportunity_cancelled') NOT NULL;`. Restart contributor_service so its queue gets the `opportunity.cancelled` binding.
- New error codes: `OPPORTUNITY_NOT_PUBLISHED`, `OPPORTUNITY_CANCELLED`. `OPPORTUNITY_NOT_OPEN` and `WORK_ALREADY_SUBMITTED` gain endpoints. See [error-codes.md](../error-codes.md).
- No `closed_at` / `cancelled_at` columns; `updated_at` records the change. Add them if reporting needs them.
- **For work submission, later:** submitting work must lock the application row (and check the opportunity isn't cancelled). Otherwise it could race a withdrawal or a cancel, because the current triggers use plain reads.
