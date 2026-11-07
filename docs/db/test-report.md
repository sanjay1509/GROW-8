# Database Test Report — Grow8 Database

**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty

This report covers the tests that check the database itself: the integrity rules, the derived views, the ORM-to-DDL match, the seed data and the SQL for the proposal's database questions. All of them run against a real MySQL 8 database, not a mock, so a passing test means MySQL enforced the rule.

## Result

**Run on Nov 7, 2026: 156 passed, 0 failed, 0 skipped.**

| Suite | Tests | Result |
|---|---|---|
| API and database tests (`grow8-backend/api/tests`) | 135 | all passed |
| Consumer service tests (`grow8-backend/services/*/tests`) | 21 | all passed |

Environment: MySQL 8.0, RabbitMQ 3.12, Python 3. Each API test starts from a fresh copy of `002_seed.sql` in a separate `grow8_test` database, so tests never touch the dev data and don't depend on each other. Applications in the tests use fixed dates, so the results don't change as real dates pass the seeded deadlines.

How to run: `make test` and `make test-services` from `grow8-backend/` with the stack up.

## Database tests by area

57 of the 135 API tests are database tests.

| File | Tests | What it proves |
|---|---|---|
| `test_db_integrity.py` | 15 | Every cross-table rule (I1–I9 in `relationship-validation.md`) is refused by MySQL when broken and accepted when followed, plus the derived views and decision 7 (verified skills). |
| `test_db_applications.py` | 8 | Decision 4: open status, deadline, applicant limit, freed places, immutable applications, and a two-connection race for the last place. |
| `test_db_workflow_seed.py` | 11 | `004_seed_workflow.sql` loads with every trigger active, the views return its history, and each of the eight database questions returns the documented answer. |
| `test_schema_mirror.py` | 19 | The ORM models match `001_schema.sql` exactly: same tables, columns, types, keys and constraints, for all 18 tables. |
| `test_notification_schema.py` | 4 | One notification per user per event, and notifications survive their opportunity being deleted. |

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
| Work only for an accepted application (I7) | `trg_work_submission_*`, `trg_application_bu` | `test_work_needs_an_accepted_application`, `test_accepted_application_with_work_cannot_be_withdrawn` |
| Only the organization owner verifies (R20) | `trg_work_verification_*` | `test_only_the_organization_owner_verifies_work` |
| Points only from approved work of the same contributor (I3, I7) | `trg_point_transaction_*` | `test_verification_points_need_an_approved_verification_of_the_same_contributor` |
| Badge points only for an earned badge (I5) | `fk_point_transaction_contributor_badge` | `test_badge_points_only_for_an_earned_badge` |
| Feedback only between the two people on the application (I2) | `trg_feedback_*` | `test_feedback_only_between_the_people_on_the_application` |
| Feedback status derived, not stored (I1) | `v_feedback_status` | `test_feedback_status_and_public_rating_use_admin_decisions_only` |
| Verified hours from approved work only (I3) | `v_contributor_verified_hours` | `test_verified_hours_count_only_approved_work` |
| Rating from approved feedback only (I3) | `v_user_rating` | `test_feedback_status_and_public_rating_use_admin_decisions_only` |
| Leaderboard summed, never stored (I3) | `v_leaderboard` | `test_leaderboard_sums_points_and_ranks_contributors` |
| Verified skill derived (decision 7) | `v_contributor_skill` | `test_skill_is_verified_only_by_approved_work_that_required_it` |
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

- `test_db_integrity.py`: the application helper now sets a fixed `submitted_at`, and the rating test uses opportunity 4, which has three places. Before, it placed three applications on opportunity 1, which has two; the new limit rule correctly refused that.
