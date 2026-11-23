# ADR 0016: Reporting opportunities and admin takedown

- **Status:** accepted
- **Date:** 2026-11-22
- **Builds on:** [ADR 0011](0011-close-and-cancel-opportunities.md) (cancelling), [ADR 0013](0013-work-verification.md) (verification refuses cancelled opportunities), [ADR 0015](0015-feedback-and-admin-review.md) (admin review pattern).

## Context

The README promises that admins "flag misleading opportunities", and the SDG 8.8 measure counts "admin-reviewed discrepancy reports and resulting flags". Until now the only way to raise a concern was feedback with `reports_discrepancy` (ADR 0015). That opens only after an accepted applicant's work is verified, weeks after a misleading or unsafe posting could do harm. Admins had no action on an opportunity at all. Issue #31.

## Decision

1. **Reporting.** Any contributor can report a published opportunity (`open` or `closed`) once, ever (`uq_opportunity_report_reporter`): `{reason, details?}`. The reason is one of `misleading_terms`, `unsafe_conditions`, `discriminatory`, `scam_or_spam` or `other`; details are optional, up to 2000 characters.
   - A draft is 404, as everywhere for other people's drafts.
   - A cancelled opportunity is 409 `OPPORTUNITY_CANCELLED`.
   - A second report is 409 `OPPORTUNITY_ALREADY_REPORTED`.
   - Creators and admins get 403.
   - The database checks the reporter's role and the opportunity's status again (`trg_opportunity_report_bi`).
2. **The reporter stays anonymous.** No creator-facing response or notification names the reporter. Admins see who reported, so they can weigh repeated or abusive reports.
3. **Admin review: one decision per report** (`uq_report_review_report`, 409 `REPORT_ALREADY_REVIEWED`).
   - **Dismiss** affects that report only. A reason is optional and is shown to the reporter.
   - **Uphold = takedown.** A reason is required (422 `TAKEDOWN_REASON_REQUIRED`, and `chk_report_review_reason` in the database), because the creator is told it. In one transaction:
     - the opportunity becomes `cancelled`;
     - every other pending report on it is marked upheld by the same admin with the same reason, so the queue clears and every reporter learns the outcome.
   - Application statuses are kept, as in ADR 0011. The opportunity leaves browse, and its applications can no longer be decided (`OPPORTUNITY_CANCELLED`). Whether a cancelled opportunity was taken down, rather than cancelled by its creator, is derived from its upheld reports and not stored.
4. **No takedown once work is submitted.** Upholding is refused with 409 `WORK_ALREADY_SUBMITTED`, the same rule as a creator's cancel (ADR 0011). Verification refuses cancelled opportunities (ADR 0013), so a takedown would strand submitted work and its hours. The report stays pending; the admin can dismiss it or handle it off-platform. Upholding a report on an opportunity its creator already cancelled is 409 `OPPORTUNITY_CANCELLED`; the admin dismisses those.
5. **Lock order: opportunity first, then the report.** Every review locks the opportunity row (`FOR UPDATE`), then the report. This avoids deadlocks:
   - **Two admins on the same posting:** a takedown writes reviews for the other pending reports. If each admin locked their own report first, two admins upholding different reports on the same opportunity would deadlock.
   - **A late report:** reporting takes a shared lock on the opportunity's status, so a report racing a takedown either lands first (and is upheld with the rest) or sees the cancel.
   - **Cancels:** a creator's cancel uses the same order.

   The "already reviewed" and "work submitted" checks are locking reads, so they see rows committed after the transaction's snapshot.
6. **Queue.** `GET /admin/reports` lists reports with each opportunity's count of open reports. The **most-reported opportunities come first**, then the oldest report. It filters by `status` (repeatable) and `opportunity_id`.
7. **Three new events (v1),** published after the commit:
   - `OPPORTUNITY_REPORTED` → **admin_service** notifies every active admin (`opportunity_reported`).
   - `OPPORTUNITY_TAKEN_DOWN` → **creator_service** tells the owner, with the reason. **contributor_service** tells each pending or accepted applicant (without the reason, since the admin wrote it for the creator) and each reporter ("thanks, it was taken down"). A reporter who also applied gets the reporter message only: one notification per person per event. All use `opportunity_taken_down`.
   - `REPORT_DISMISSED` → **contributor_service** tells the reporter, with the reason if the admin gave one (`report_dismissed`).

## Consequences

- Two new tables, `opportunity_report` and `report_review` (19 → 21), with triggers, ORM models and the ENSF 608 documents updated. `grow8_require_role_change_allowed` also locks the role of anyone with report rows. This needs `make reset-db` (wipes local data and uploaded files). To keep your data instead, run the two `CREATE TABLE` statements, the new procedure and triggers from `001_schema.sql`, the updated `grow8_require_role_change_allowed`, and:

  ```sql
  ALTER TABLE notification MODIFY notification_type ENUM('opportunity_created', 'opportunity_published', 'application_submitted', 'application_decided', 'application_withdrawn', 'opportunity_cancelled', 'work_submitted', 'work_verified', 'work_rejected', 'feedback_submitted', 'feedback_approved', 'feedback_rejected', 'opportunity_reported', 'opportunity_taken_down', 'report_dismissed') NOT NULL;
  ```

  Restart all three consumers for the new bindings.
- A posting with submitted work can't be taken down in-app (decision 4). Revisit together with ADR 0011 and ADR 0013 if that becomes a problem.
- New error codes: `OPPORTUNITY_ALREADY_REPORTED`, `REPORT_ALREADY_REVIEWED`, `TAKEDOWN_REASON_REQUIRED`, `REPORT_NOT_FOUND`. `OPPORTUNITY_NOT_FOUND`, `OPPORTUNITY_CANCELLED`, `WORK_ALREADY_SUBMITTED` and `ROLE_FORBIDDEN` gain endpoints. See [error-codes.md](../error-codes.md).
