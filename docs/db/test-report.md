# Database Test Report — Grow8 Database

**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty

This report covers the tests that check the database itself: the integrity rules, the derived views, the ORM-to-DDL match, the seed data and the SQL for the proposal's database questions. All of them run against a real MySQL 8 database, not a mock, so a passing test means MySQL enforced the rule.

## Result

**Run on Nov 22, 2026: 795 passed, 0 failed, 0 skipped.**

| Suite | Tests | Result |
|---|---|---|
| API and database tests (`grow8-backend/api/tests`) | 700 | all passed |
| Consumer service tests (`grow8-backend/services/*/tests`) | 95 | all passed |

Environment: MySQL 8.0, RabbitMQ 3.12, Python 3. Each API test starts from a fresh copy of `002_seed.sql` in a separate `grow8_test` database, so tests never touch the dev data and don't depend on each other. Applications in the tests use fixed dates, so the results don't change as real dates pass the seeded deadlines.

How to run: `make test` and `make test-services` from `grow8-backend/` with the stack up.

## Database tests by area

76 of the 700 API tests are database tests. The other API tests (endpoints, file uploads, auth) also run against the real database, but they test the API's behaviour rather than a database rule.

| File | Tests | What it proves |
|---|---|---|
| `test_db_integrity.py` | 18 | Every cross-table rule (I1–I9 in `relationship-validation.md`) is refused by MySQL when broken and accepted when followed, plus the derived views, decision 7 (verified skills, listed or earned) and the `contributor_resume` constraints. |
| `test_db_applications.py` | 8 | Decision 4: open status, deadline, applicant limit, freed places, immutable applications, and a two-connection race for the last place. |
| `test_db_workflow_seed.py` | 11 | `004_seed_workflow.sql` loads with every trigger active, the views return its history, and each of the eight database questions returns the documented answer. |
| `test_schema_mirror.py` | 22 | The ORM models match `001_schema.sql` exactly: same tables, columns, types, keys and constraints, for all 21 tables. |
| `test_notification_schema.py` | 4 | One notification per user per event, and notifications survive their opportunity being deleted. |
| `test_submission_repository.py` | 5 | Work submissions and their attachments are stored and read back, an attachment is found only through its own submission, and MySQL refuses work for an application that isn't accepted (I7) and a second submission for the same application (R9). |

| `test_db_reports.py` | 8 | Opportunity reports (R24–R27): only contributors report and only admins review (I6), only open or closed opportunities can be reported (I7), one report per contributor per opportunity and one review per report, a takedown always has a reason, and report rows lock the account's role. |

## Rules covered

Each rule has at least one accepted and one refused case.

| Rule | Enforced by | Test |
|---|---|---|
| Profile and organization roles (I6) | `trg_contributor_profile_*`, `trg_creator_organization_*` | `test_contributor_profile_requires_contributor_role`, `test_organization_owner_requires_creator_role` |
| Only admins review feedback (I6) | `trg_admin_review_*` | `test_admin_review_requires_admin_role` |
| Role locked once rows depend on it (I6) | `trg_user_account_bu` | `test_role_cannot_change_once_rows_depend_on_it` |
| Apply only while open (I7) | `trg_application_bi` | `test_cannot_apply_to_an_opportunity_that_is_not_open` |
| Apply only before the deadline (I7) | `trg_application_bi` | `test_cannot_apply_after_the_deadline` |
| Applicant limit, pending + accepted (decision 4) | `trg_application_bi/bu`, row lock | `test_applications_fill_up_to_the_limit_and_no_further`, `test_rejected_and_withdrawn_applications_free_their_place`, `test_inactive_applications_skip_the_capacity_check` |
| No race for the last place (decision 4) | `SELECT … FOR UPDATE` on the opportunity | `test_two_people_racing_for_the_last_place_cannot_both_get_it` |
| Application cannot move or be re-dated | `trg_application_bi/bu` | `test_application_cannot_move_or_be_backdated_later`, `test_application_cannot_be_dated_in_the_future` |
| Work only for an accepted application (I7) | `trg_work_submission_*`, `trg_application_bu` | `test_work_needs_an_accepted_application`, `test_accepted_application_with_work_cannot_be_withdrawn`, `test_the_trigger_refuses_work_for_an_application_that_is_not_accepted` |
| At most one submission per application (R9) | `uq_work_submission_application` | `test_a_second_submission_breaks_the_unique_key` |
| Only the organization owner verifies (R20) | `trg_work_verification_*` | `test_only_the_organization_owner_verifies_work` |
| Points only from approved work of the same contributor (I3, I7) | `trg_point_transaction_*` | `test_verification_points_need_an_approved_verification_of_the_same_contributor` |
| Badge points only for an earned badge (I5) | `fk_point_transaction_contributor_badge` | `test_badge_points_only_for_an_earned_badge` |
| Feedback only between the two people on the application (I2) | `trg_feedback_*` | `test_feedback_only_between_the_people_on_the_application` |
| Feedback status derived, not stored (I1) | `v_feedback_status` | `test_feedback_status_and_public_rating_use_admin_decisions_only` |
| Verified hours from approved work only (I3) | `v_contributor_verified_hours` | `test_verified_hours_count_only_approved_work` |
| Rating from approved feedback only (I3) | `v_user_rating` | `test_feedback_status_and_public_rating_use_admin_decisions_only` |
| Leaderboard summed, never stored (I3) | `v_leaderboard` | `test_leaderboard_sums_points_and_ranks_contributors` |
| Verified skill derived, listed or earned (decision 7, ADR 0019) | `v_contributor_skill` | `test_skill_is_verified_only_by_approved_work_that_required_it`, `test_an_earned_skill_stays_when_its_listing_is_removed`, `test_an_earned_skill_is_one_row_with_its_first_approval` |
| Reporters are contributors, report reviewers are admins (I6, R25, R27) | `trg_opportunity_report_*`, `trg_report_review_*` | `test_only_contributors_report`, `test_only_admins_review_reports` |
| Only published opportunities can be reported (I7, R24) | `trg_opportunity_report_bi` | `test_only_published_opportunities_can_be_reported` |
| One report per contributor per opportunity, one review per report (R25, R26) | `uq_opportunity_report_reporter`, `uq_report_review_report` | `test_one_report_per_contributor_per_opportunity`, `test_each_report_is_reviewed_once` |
| A takedown always has a reason | `chk_report_review_reason` | `test_a_takedown_always_has_a_reason` |
| One resume per contributor, non-empty, unique storage key, deleted with the profile (R23) | `contributor_resume` PK = FK, `chk_contributor_resume_size`, `uq_contributor_resume_storage_key`, `ON DELETE CASCADE` | `test_contributor_resume_is_one_per_contributor_and_goes_with_the_profile` |
| Discrepancy flag on feedback | `feedback.reports_discrepancy` | `test_feedback_can_report_a_discrepancy`, `test_q7_open_discrepancy_reports` |
| One notification per user per event (R21) | `uq_notification_event_user` | `test_same_event_for_same_user_is_stored_once`, `test_same_event_notifies_each_user_once` |

## Concurrency test in detail

`test_two_people_racing_for_the_last_place_cannot_both_get_it` opens two real connections on opportunity 2, which has one place:

1. Connection A starts a transaction and applies. Its trigger locks the opportunity row and the application is inserted, but not committed.
2. Connection B applies from another thread. Its trigger asks for the same row lock and waits. The test checks that B is still waiting after one second.
3. A commits. B gets the lock, counts the active applications with a locking read, sees A's committed row and is refused with `applicant_limit_reached`.
4. Exactly one active application exists afterwards.

Without the row lock, both transactions would count zero active applications and both would get in.

## Changes made for this report

- Nov 22 (earned skills, ADR 0019): `v_contributor_skill` now returns every listed skill plus every skill earned through approved work, with `is_listed`. `test_db_integrity.py` rewrites the decision 7 test (approved work on an opportunity requiring unlisted skills now verifies them) and adds two: a listed skill that work proved stays verified when its listing is removed, and two approvals proving the same skill give one row with the first date. `test_db_workflow_seed.py` now expects the seed's earned skills (Alex's 7 and 9, Jordan's 10).
- Nov 22 (creator organization, ADR 0018): no schema change. `test_organization.py` relies on `trg_creator_organization_bi` accepting a creator's first organization, and adds a two-connection race: two first saves by a creator without an organization. The second waits on the creator's account lock and edits the organization the first created, instead of failing on `uq_creator_organization_owner`.
- Nov 22 (contributor profile, ADR 0017): no schema change, so the database tests are unchanged. `test_contributor_profile.py` reads `verified` from `v_contributor_skill` (a skill turns verified once approved work on an opportunity that required it exists, and comes back with its original date after being removed and re-added), and adds a two-connection race: two first saves for a contributor without a profile row. The second waits for the first's lock instead of failing on the primary key.
- Nov 22 (reports and takedown, ADR 0016): two new tables, `opportunity_report` and `report_review` (19 → 21), with `test_db_reports.py` for their rules and the schema mirror covering both. `notification_type` gained `opportunity_reported`, `opportunity_taken_down` and `report_dismissed`. `test_report_service.py` adds two two-connection races: two admins upholding different reports on the same opportunity (the second waits on the opportunity lock and finds its report already upheld; locking the report first deadlocks, which the test catches), and a report racing a takedown (it waits and sees the cancel).
- Nov 22 (feedback and admin review, ADR 0015): counts updated. `notification_type` gained `feedback_submitted`, `feedback_approved` and `feedback_rejected` (covered by `test_db_notifier.py`, which also tests the new `find_active_admins` query). `test_feedback_service.py` checks that pending and rejected feedback never change `v_user_rating`, and adds a two-connection race: a second admin review of the same feedback waits for the first one's row lock and is refused by the locking read, not by `uq_admin_review_feedback`.
- Nov 22 (work verification, ADR 0013): counts updated for the work verification feature. `notification_type` gained `work_verified` and `work_rejected` (covered by `test_db_notifier.py`). `test_verification_service.py` adds a two-connection race like the one above: a second verification of the same submission waits for the first one's row lock, then its locking read sees the committed verification and it is refused with `SUBMISSION_ALREADY_VERIFIED`, not by the unique-key backstop.
- Nov 17 (work submission, ADR 0012): added `test_submission_repository.py`, and counts updated for the work submission feature. `notification_type` gained `work_submitted`; `test_db_notifier.py` now checks that every notification type can be stored once per event.
- Nov 17: added the `contributor_resume` test after the table was added on Nov 15 (ADR 0008); counts updated for the application lifecycle and resume features.
- `test_db_integrity.py`: the application helper now sets a fixed `submitted_at`, and the rating test uses opportunity 4, which has three places. Before, it placed three applications on opportunity 1, which has two; the new limit rule correctly refused that.
