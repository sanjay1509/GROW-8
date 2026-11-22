# ADR 0015: Feedback between participants and admin review

- **Status:** accepted
- **Date:** 2026-11-22
- **Builds on:** [ADR 0013](0013-work-verification.md) (verified work), [ADR 0006](0006-application-lifecycle.md) (visibility), [ADR 0010](0010-delayed-retry-before-dead-letter.md) (queues). ADR 0014 is reserved for rewards (#24).

## Context

Once work is verified, the contributor and the creator should be able to rate each other, and the platform needs public ratings people can trust. The proposal makes admins the moderators: only feedback an admin approves counts. The schema has had this from the start:
- `feedback`: one per author per application (`uq_feedback_application_author`), rated 1–5, never about yourself. `trg_feedback_bi/bu` refuse anyone who isn't one of the two people on the application.
- `admin_review`: one per feedback (`uq_admin_review_feedback`); `trg_admin_review_bi/bu` refuse a reviewer who isn't an admin.
- `v_feedback_status`: pending until reviewed.
- `v_user_rating`: the average and count of approved feedback only.

Nothing could write feedback yet, and admin_service had no handlers.

## Decision

1. **Who and when.** The applicant and the creator who owns the opportunity can each leave one feedback on the application, about the other one. The subject is never chosen by the client: it is always the other participant. Feedback is allowed once the work has been verified, approved or rejected (409 `WORK_NOT_VERIFIED` before that), since that is when both sides know how it went. Anyone else gets 404, as for the application itself (ADR 0006).
2. **What.** `{rating, comment?, reports_discrepancy?}`: a whole number from 1 to 5, an optional comment of up to 2000 characters (trimmed), and a flag for "something on this application went wrong", such as disputed hours or a decision. Once given, feedback can't be edited or withdrawn (409 `FEEDBACK_ALREADY_SUBMITTED`), so what the admin reviews is what gets published.
3. **Visibility: moderation first.**
   - The **author** always sees their own feedback with its status (`pending`, `approved` or `rejected`) and the admin's review, including any reason.
   - The **subject** sees feedback about them **only once it is approved**. Pending or rejected feedback (abusive, retaliatory, or still disputed) stays hidden from them, which is the point of moderation.
   - `GET /applications/{id}/feedback` returns `{given, received}` for the caller, each `null` when there's nothing to show.
4. **Admin review.**
   - Each feedback is reviewed once (409 `FEEDBACK_ALREADY_REVIEWED`): approve, or reject with a reason (422 `REJECTION_REASON_REQUIRED`). The reason is up to 500 characters, optional when approving.
   - Reviewing locks the feedback row and reads any existing review with a locking read, so two admins can't both decide. The unique key remains the backstop.
   - The queue (`GET /admin/feedback`) shows discrepancy reports first, then the oldest feedback first. It filters by `status` (repeatable) and `discrepancy`.
   - Non-admins get 403 on admin routes.
5. **Ratings are computed, never stored.** `GET /users/{id}/rating` is public and reads `v_user_rating`: the average of approved feedback (2 decimals) and its count. With no approved feedback, the average is `null` and the count is 0. Pending and rejected feedback never move it.
6. **Check twice, report once.** The service checks every rule first. The database errors map to the same codes, never a 500:
   - `feedback_participants` (trigger) → 404 `APPLICATION_NOT_FOUND`
   - `uq_feedback_application_author` → `FEEDBACK_ALREADY_SUBMITTED`
   - `uq_admin_review_feedback` → `FEEDBACK_ALREADY_REVIEWED`
7. **Three new events (v1),** published after the commit:
   - `FEEDBACK_SUBMITTED` → **admin_service** notifies every active admin (`feedback_submitted`). This is admin_service's first handler, so it now runs the shared consumer and declares `grow8.admin_service`, its retry queues and its DLQ.
   - `FEEDBACK_APPROVED` → the author is told it was published, and the subject is told they received a rating (`feedback_approved`).
   - `FEEDBACK_REJECTED` → **only the author** is told, with the admin's reason (`feedback_rejected`). The subject never hears about feedback that doesn't count, consistent with decision 3.

   The two decision events go to both **creator_service** and **contributor_service**. Each event says whether the author is the contributor or the creator, and each service notifies only its own side: contributor_service the contributor, creator_service the creator. Each person gets exactly one notification per event.

## Consequences

- `notification.notification_type` gains `feedback_submitted`, `feedback_approved` and `feedback_rejected`: run `make reset-db` (wipes local data and uploaded files), or keep your data with:

  ```sql
  ALTER TABLE notification MODIFY notification_type ENUM('opportunity_created', 'opportunity_published', 'application_submitted', 'application_decided', 'application_withdrawn', 'opportunity_cancelled', 'work_submitted', 'work_verified', 'work_rejected', 'feedback_submitted', 'feedback_approved', 'feedback_rejected') NOT NULL;
  ```

  Restart all three consumers so their queues get the new bindings (admin_service declares its queue for the first time).
- The issue says both participants see the feedback and that both are notified of each decision. This ADR narrows both for the subject, as decisions 3 and 7 explain.
- New error codes: `WORK_NOT_VERIFIED`, `FEEDBACK_ALREADY_SUBMITTED`, `FEEDBACK_ALREADY_REVIEWED`, `REJECTION_REASON_REQUIRED`, `FEEDBACK_NOT_FOUND`, `USER_NOT_FOUND`. See [error-codes.md](../error-codes.md).
- Feedback is final for the MVP: no editing, no appeal of a rejection.
