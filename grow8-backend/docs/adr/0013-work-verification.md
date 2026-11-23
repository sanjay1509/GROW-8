# ADR 0013: Verifying submitted work

- **Status:** accepted
- **Date:** 2026-11-22
- **Builds on:** [ADR 0012](0012-work-submission.md) (work submission), [ADR 0011](0011-close-and-cancel-opportunities.md) (cancelled opportunities, lock order), [ADR 0006](0006-application-lifecycle.md) (visibility).

## Context

Since ADR 0012, an accepted contributor can submit their work, and the creator is notified, but nothing could happen next. Verified hours, verified skills (`v_contributor_verified_hours`, `v_contributor_skill`), points and badges, and feedback all depend on a creator's decision about the work. The schema has had `work_verification` from the start: one row per submission (`uq_work_verification_submission`), approved with hours or rejected without them (`chk_work_verification_hours`), and `trg_work_verification_bi/bu` already refuse a verifier who doesn't own the opportunity's organization.

## Decision

1. **Who and when.** Only the creator who owns the opportunity's organization verifies, and only while the opportunity isn't `cancelled` (409 `OPPORTUNITY_CANCELLED`). A `closed` opportunity is fine. Cancelling is already refused once work is submitted (ADR 0011), so in practice this only guards data that got there some other way; it keeps the rule the same as for deciding and submitting.
2. **One decision, final.** Each submission is verified once (409 `SUBMISSION_ALREADY_VERIFIED`). There is no changing your mind: approved hours feed the views, points and badges, and taking them back would need reversals everywhere.
3. **`POST /submissions/{id}/verification`**, body `{decision, verified_hours?, comment?}`:
   - `approved`: `verified_hours` is required, `> 0` with two decimals, and at most the hours the contributor claimed (422 `VERIFIED_HOURS_EXCEED_CLAIMED`). A creator can verify fewer hours than claimed, never more. The comment is optional.
   - `rejected`: a comment is required (422 `REJECTION_COMMENT_REQUIRED`), so the contributor learns why. `verified_hours` must be left out.
   - Comments are 1–2000 characters, trimmed. A missing `verified_hours` on approval, or one sent with a rejection, is the usual 422 `VALIDATION_ERROR`.
4. **Concurrency.** Verifying locks the submission row (`FOR UPDATE`), then takes a shared lock on the opportunity's status (`FOR SHARE`), and reads any existing verification with a locking read, so it sees one committed a moment ago. Two decisions on the same submission are serialized: the second sees the first and gets 409. Cancelling locks the opportunity but never the submission, so the two can't deadlock. The trigger and the unique key remain the backstop: `verifier_not_owner` maps to 404, and a duplicate on `uq_work_verification_submission` maps to `SUBMISSION_ALREADY_VERIFIED`. A race never surfaces as a 500.
5. **Visibility.** `GET /submissions/{id}` is for the applicant and the owning creator. To anyone else the submission doesn't exist (404 `SUBMISSION_NOT_FOUND`), the same as for applications (ADR 0006). The applicant sees the decision, hours and comment.
6. **Review queue.** `GET /submissions/received` lists submissions to the creator's opportunities, filterable by `status` (`awaiting`, `approved`, `rejected`, repeatable) and `opportunity_id`, and paginated. The oldest submission comes first, so work that has waited longest is reviewed first. `status` is derived: `awaiting` means there is no verification row yet.
7. **Submissions carry their verification.** Every submission response gains `status`, `verification` (`null` until decided), a short `opportunity` and the `applicant`'s id and name. The review queue then needs no request per row. These fields are additive.
8. **Applications carry a derived `work_status`:** `not_submitted` (no submission, including every application that was never accepted), `awaiting_verification`, `completed` (approved) or `work_rejected`. It is derived from the submission and its verification, with no new column.
9. **Two new events (v1), published after the commit:** `WORK_VERIFIED` and `WORK_REJECTED`. **contributor_service** notifies the contributor ("Your work on … was verified (6 h)", or the rejection with the creator's comment), with notification types `work_verified` and `work_rejected`. `WORK_VERIFIED` carries `verification_id` and `verified_hours`, so the rewards handler (#24) can award points once per verification without re-deriving them.

## Consequences

- `notification.notification_type` gains `work_verified` and `work_rejected`: run `make reset-db` (wipes local data and uploaded files), or keep your data with:

  ```sql
  ALTER TABLE notification MODIFY notification_type ENUM('opportunity_created', 'opportunity_published', 'application_submitted', 'application_decided', 'application_withdrawn', 'opportunity_cancelled', 'work_submitted', 'work_verified', 'work_rejected') NOT NULL;
  ```

  Restart contributor_service so its queue gets the `work.verified` and `work.rejected` bindings.
- Verified hours and verified skills now change through the API: the views already count only approved verifications, so nothing is stored or updated by hand.
- New error codes: `SUBMISSION_ALREADY_VERIFIED`, `VERIFIED_HOURS_EXCEED_CLAIMED`, `REJECTION_COMMENT_REQUIRED`. `SUBMISSION_NOT_FOUND` and `OPPORTUNITY_CANCELLED` gain endpoints. See [error-codes.md](../error-codes.md).
- A rejected submission is final for the MVP, as in ADR 0012: the contributor can't resubmit.
