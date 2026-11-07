# Data Dictionary — Grow8 Database

**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty

> Generated Oct 27, 2026 from the loaded schema (`grow8-backend/db/init/001_schema.sql`): 18 tables, 124 columns, 4 views, 16 triggers. Types, nullability, defaults and keys are read from MySQL's `information_schema`, so they match the DDL exactly; descriptions are written by hand. Rules referenced as R1–R22 and I1–I9 are explained in `relationship-validation.md`; keys and normal forms are in `functional-dependencies.md`.

## How to read this

- **Type**: MySQL column type. `int unsigned` keys, `decimal(6,2)` hours, `datetime` in UTC. `enum(...)` lists every allowed value.
- **Null**: `NO` means a value is required.
- **Default**: value used when the insert leaves the column out. *now* is `CURRENT_TIMESTAMP`.
- **Key**: `PK` primary key · `FK → table.column` foreign key · `UQ` unique on its own · `UQ*` part of a multi-column unique key (named under the table).
- Under each table: its unique keys, foreign keys with their `ON DELETE` rule, `CHECK` constraints, and the triggers that enforce rules a key or check cannot.

## Tables at a glance

| # | Table | Purpose | Columns |
|---|---|---|---|
| 1 | [`user_account`](#user_account) | One row per person who can sign in. `role` decides which profile tables the account may have (R1, R2, R15). | 8 |
| 2 | [`contributor_profile`](#contributor_profile) | Extra details for a contributor account (shared primary key with `user_account`, 1 : 0..1). | 7 |
| 3 | [`creator_organization`](#creator_organization) | The business, nonprofit or event organizer a creator account manages. One organization per creator in the MVP. | 9 |
| 4 | [`opportunity_category`](#opportunity_category) | Fixed list of opportunity categories (knowledge-based or community). | 4 |
| 5 | [`skill`](#skill) | Fixed list of skills that opportunities ask for and contributors have. | 3 |
| 6 | [`opportunity`](#opportunity) | A short-term task a creator's organization posts. Drafts may be incomplete; a published opportunity must carry every mandatory disclosure (`chk_opportunity_published_complete`, ADR 0001). | 23 |
| 7 | [`opportunity_skill`](#opportunity_skill) | Skills an opportunity asks for (M : N between `opportunity` and `skill`). | 2 |
| 8 | [`contributor_skill`](#contributor_skill) | Skills a contributor has (M : N between `contributor_profile` and `skill`). | 4 |
| 9 | [`application`](#application) | A contributor applying for an opportunity. One application per contributor per opportunity. | 7 |
| 10 | [`work_submission`](#work_submission) | The contributor's claim that the work for an accepted application is done. At most one per application. | 5 |
| 11 | [`submission_attachment`](#submission_attachment) | Metadata for a file attached to a submission. The file itself is stored outside MySQL. | 7 |
| 12 | [`work_verification`](#work_verification) | The creator's decision on a submission. Approved hours here are the only source of verified hours. | 7 |
| 13 | [`feedback`](#feedback) | A rating one participant of an application gives the other. Its status is derived from `admin_review` (`v_feedback_status`). | 7 |
| 14 | [`admin_review`](#admin_review) | An admin's decision on one feedback. No row means the feedback is still pending. | 6 |
| 15 | [`badge`](#badge) | Badges contributors can earn, and the points each one is worth. | 6 |
| 16 | [`contributor_badge`](#contributor_badge) | Badges a contributor has earned. Each badge is earned once. | 3 |
| 17 | [`point_transaction`](#point_transaction) | Ledger of points awarded, either for approved work or for a badge. Leaderboard totals are summed from it, never stored. | 7 |
| 18 | [`notification`](#notification) | One message per user per event, written by the consumer services and read by the frontend through `/api/v1/notifications` (ADR 0003). Not in the original 17-entity proposal. | 9 |

## 1. Accounts and organizations

### user_account

One row per person who can sign in. `role` decides which profile tables the account may have (R1, R2, R15).

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `user_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `email` | `varchar(255)` | NO |  | UQ | Sign-in email; unique. |
| `password_hash` | `varchar(255)` | NO |  |  | bcrypt hash of the password. The password itself is never stored. |
| `role` | `enum('creator','contributor','admin')` | NO |  |  | `creator`, `contributor` or `admin`. Locked once role-specific rows exist (`trg_user_account_bu`). |
| `full_name` | `varchar(150)` | NO |  |  | Display name. |
| `is_active` | `tinyint(1)` | NO | `1` |  | 0 disables sign-in without deleting the account. |
| `created_at` | `datetime` | NO | now |  | When the row was created. |
| `updated_at` | `datetime` | NO | now (updates on change) |  | When the row last changed. |

- **Unique:** `uq_user_account_email` (email)
- **Triggers:** `trg_user_account_bu`

### contributor_profile

Extra details for a contributor account (shared primary key with `user_account`, 1 : 0..1).

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `user_id` | `int unsigned` | NO |  | PK, FK → user_account.user_id | The contributor's account. Must have role `contributor` (`trg_contributor_profile_*`). |
| `headline` | `varchar(150)` | YES |  |  | Short tagline shown on the profile. |
| `bio` | `text` | YES |  |  | Longer description. |
| `institution` | `varchar(150)` | YES |  |  | School or employer, optional. |
| `city` | `varchar(100)` | YES |  |  | City, used for local matching. |
| `created_at` | `datetime` | NO | now |  | When the row was created. |
| `updated_at` | `datetime` | NO | now (updates on change) |  | When the row last changed. |

- **Foreign keys:** `fk_contributor_profile_user` (user_id) → `user_account` (cascade on delete)
- **Triggers:** `trg_contributor_profile_bi`, `trg_contributor_profile_bu`

### creator_organization

The business, nonprofit or event organizer a creator account manages. One organization per creator in the MVP.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `organization_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `owner_user_id` | `int unsigned` | NO |  | FK → user_account.user_id, UQ | The creator account that manages it. Must have role `creator`; unique. |
| `name` | `varchar(150)` | NO |  |  | Organization name. |
| `organization_type` | `enum('small_business','nonprofit','event_organizer','other')` | NO |  |  | `small_business`, `nonprofit`, `event_organizer` or `other`. |
| `description` | `text` | YES |  |  | About the organization. |
| `website` | `varchar(255)` | YES |  |  | Public website URL. |
| `city` | `varchar(100)` | YES |  |  | City where it operates. |
| `created_at` | `datetime` | NO | now |  | When the row was created. |
| `updated_at` | `datetime` | NO | now (updates on change) |  | When the row last changed. |

- **Unique:** `uq_creator_organization_owner` (owner_user_id)
- **Foreign keys:** `fk_creator_organization_owner` (owner_user_id) → `user_account` (cascade on delete)
- **Triggers:** `trg_creator_organization_bi`, `trg_creator_organization_bu`

## 2. Reference data

### opportunity_category

Fixed list of opportunity categories (knowledge-based or community).

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `category_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `code` | `varchar(30)` | NO |  | UQ | Stable identifier used by the API (`knowledge`, `community`). |
| `name` | `varchar(100)` | NO |  | UQ | Display name. |
| `description` | `varchar(255)` | YES |  |  | What kind of work belongs in the category. |

- **Unique:** `uq_opportunity_category_code` (code); `uq_opportunity_category_name` (name)

### skill

Fixed list of skills that opportunities ask for and contributors have.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `skill_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `code` | `varchar(50)` | NO |  | UQ | Stable identifier used by the API, e.g. `data-entry`. |
| `name` | `varchar(100)` | NO |  | UQ | Display name. |

- **Unique:** `uq_skill_code` (code); `uq_skill_name` (name)

## 3. Opportunities and skills

### opportunity

A short-term task a creator's organization posts. Drafts may be incomplete; a published opportunity must carry every mandatory disclosure (`chk_opportunity_published_complete`, ADR 0001).

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `opportunity_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `organization_id` | `int unsigned` | NO |  | FK → creator_organization.organization_id | The organization posting it. |
| `category_id` | `int unsigned` | NO |  | FK → opportunity_category.category_id | Its category. |
| `title` | `varchar(200)` | NO |  |  | Short title. |
| `description` | `text` | NO |  |  | What the work is. |
| `requirements` | `text` | YES |  |  | What a contributor needs. Mandatory to publish. |
| `location` | `varchar(255)` | YES |  |  | Address or area. |
| `work_mode` | `enum('on_site','remote','hybrid')` | YES |  |  | `on_site`, `remote` or `hybrid`. |
| `start_date` | `date` | YES |  |  | First day of the work. Mandatory to publish. |
| `end_date` | `date` | YES |  |  | Last day; not before `start_date`. Mandatory to publish. |
| `expected_hours` | `decimal(6,2)` | YES |  |  | Estimated hours; greater than 0. Mandatory to publish. |
| `compensation_type` | `enum('paid','stipend','unpaid')` | YES |  |  | `paid`, `stipend` or `unpaid`. Mandatory to publish. |
| `compensation_amount` | `decimal(10,2)` | YES |  |  | Amount; 0 or more. Required to publish unless `unpaid`. |
| `compensation_details` | `varchar(500)` | YES |  |  | Free-text notes on compensation (e.g. honorarium, meals). |
| `applicant_limit` | `smallint unsigned` | YES |  |  | Maximum applicants; greater than 0. Mandatory to publish. Enforced by the apply endpoint (decision 4). |
| `application_deadline` | `datetime` | YES |  |  | Last moment to apply. Mandatory to publish. |
| `working_conditions` | `text` | YES |  |  | Disclosure of working conditions. Mandatory to publish. |
| `safety_information` | `text` | YES |  |  | Disclosure of safety information. Mandatory to publish. |
| `accessibility_details` | `text` | YES |  |  | Disclosure of accessibility. Mandatory to publish. |
| `status` | `enum('draft','open','closed','cancelled')` | NO | `draft` |  | `draft`, `open`, `closed` or `cancelled`. Publishing moves `draft` to `open` and emits `OPPORTUNITY_CREATED`. |
| `published_at` | `datetime` | YES |  |  | When it was published; set together with `status = open`. |
| `created_at` | `datetime` | NO | now |  | When the row was created. |
| `updated_at` | `datetime` | NO | now (updates on change) |  | When the row last changed. |

- **Foreign keys:** `fk_opportunity_category` (category_id) → `opportunity_category` (restrict on delete); `fk_opportunity_organization` (organization_id) → `creator_organization` (restrict on delete)
- **Checks:** `chk_opportunity_applicant_limit`, `chk_opportunity_compensation_amount`, `chk_opportunity_dates`, `chk_opportunity_expected_hours`, `chk_opportunity_published_complete`

### opportunity_skill

Skills an opportunity asks for (M : N between `opportunity` and `skill`).

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `opportunity_id` | `int unsigned` | NO |  | PK, FK → opportunity.opportunity_id | The opportunity. Rows are deleted with it. |
| `skill_id` | `int unsigned` | NO |  | PK, FK → skill.skill_id | A skill it asks for. |

- **Foreign keys:** `fk_opportunity_skill_opportunity` (opportunity_id) → `opportunity` (cascade on delete); `fk_opportunity_skill_skill` (skill_id) → `skill` (restrict on delete)

### contributor_skill

Skills a contributor has (M : N between `contributor_profile` and `skill`).

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `contributor_id` | `int unsigned` | NO |  | PK, FK → contributor_profile.user_id | The contributor. Rows are deleted with the profile. |
| `skill_id` | `int unsigned` | NO |  | PK, FK → skill.skill_id | A skill they have. |
| `source` | `enum('self_reported','verified')` | NO | `self_reported` |  | `self_reported` or `verified` (meaning still open, decision 7). |
| `created_at` | `datetime` | NO | now |  | When the skill was added. |

- **Foreign keys:** `fk_contributor_skill_contributor` (contributor_id) → `contributor_profile` (cascade on delete); `fk_contributor_skill_skill` (skill_id) → `skill` (restrict on delete)

## 4. Applications, work and verification

### application

A contributor applying for an opportunity. One application per contributor per opportunity.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `application_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `opportunity_id` | `int unsigned` | NO |  | FK → opportunity.opportunity_id, UQ* | The opportunity applied for. |
| `contributor_id` | `int unsigned` | NO |  | FK → contributor_profile.user_id, UQ* | The applying contributor. |
| `status` | `enum('pending','accepted','rejected','withdrawn')` | NO | `pending` |  | `pending`, `accepted`, `rejected` or `withdrawn`. Cannot leave `accepted` once work is submitted (`trg_application_bu`). |
| `motivation` | `text` | YES |  |  | The contributor's note to the creator. |
| `submitted_at` | `datetime` | NO | now |  | When the application was sent. |
| `decided_at` | `datetime` | YES |  |  | When the creator accepted or rejected it; required for those two statuses (`chk_application_decided`). |

- **Unique:** `uq_application_contributor_opportunity` (contributor_id, opportunity_id)
- **Foreign keys:** `fk_application_contributor` (contributor_id) → `contributor_profile` (restrict on delete); `fk_application_opportunity` (opportunity_id) → `opportunity` (restrict on delete)
- **Checks:** `chk_application_decided`
- **Triggers:** `trg_application_bu`

### work_submission

The contributor's claim that the work for an accepted application is done. At most one per application.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `submission_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `application_id` | `int unsigned` | NO |  | FK → application.application_id, UQ | The application; must be `accepted` (`trg_work_submission_*`). Unique. |
| `description` | `text` | NO |  |  | What the contributor did. |
| `hours_claimed` | `decimal(6,2)` | NO |  |  | Hours the contributor reports; greater than 0. |
| `submitted_at` | `datetime` | NO | now |  | When it was submitted. |

- **Unique:** `uq_work_submission_application` (application_id)
- **Foreign keys:** `fk_work_submission_application` (application_id) → `application` (restrict on delete)
- **Checks:** `chk_work_submission_hours`
- **Triggers:** `trg_work_submission_bi`, `trg_work_submission_bu`

### submission_attachment

Metadata for a file attached to a submission. The file itself is stored outside MySQL.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `attachment_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `submission_id` | `int unsigned` | NO |  | FK → work_submission.submission_id | The submission. Rows are deleted with it. |
| `file_name` | `varchar(255)` | NO |  |  | Original file name. |
| `content_type` | `varchar(100)` | NO |  |  | MIME type, e.g. `application/pdf`. |
| `size_bytes` | `bigint unsigned` | NO |  |  | File size in bytes. |
| `storage_key` | `varchar(512)` | NO |  | UQ | Key of the file in external storage; unique. |
| `uploaded_at` | `datetime` | NO | now |  | When it was uploaded. |

- **Unique:** `uq_submission_attachment_storage_key` (storage_key)
- **Foreign keys:** `fk_submission_attachment_submission` (submission_id) → `work_submission` (cascade on delete)

### work_verification

The creator's decision on a submission. Approved hours here are the only source of verified hours.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `verification_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `submission_id` | `int unsigned` | NO |  | FK → work_submission.submission_id, UQ | The submission decided on. Unique, so hours can't be counted twice. |
| `verified_by_user_id` | `int unsigned` | NO |  | FK → user_account.user_id | The creator who decided. Must own the opportunity's organization (`trg_work_verification_*`, R20). |
| `decision` | `enum('approved','rejected')` | NO |  |  | `approved` or `rejected`. |
| `verified_hours` | `decimal(6,2)` | YES |  |  | Hours accepted; required and greater than 0 when approved, empty when rejected (`chk_work_verification_hours`). |
| `comment` | `text` | YES |  |  | Creator's note to the contributor. |
| `verified_at` | `datetime` | NO | now |  | When the decision was made. |

- **Unique:** `uq_work_verification_submission` (submission_id)
- **Foreign keys:** `fk_work_verification_submission` (submission_id) → `work_submission` (restrict on delete); `fk_work_verification_verified_by` (verified_by_user_id) → `user_account` (restrict on delete)
- **Checks:** `chk_work_verification_hours`
- **Triggers:** `trg_work_verification_bi`, `trg_work_verification_bu`

## 5. Feedback and moderation

### feedback

A rating one participant of an application gives the other. Its status is derived from `admin_review` (`v_feedback_status`).

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `feedback_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `application_id` | `int unsigned` | NO |  | FK → application.application_id, UQ* | The application the feedback is about. |
| `author_user_id` | `int unsigned` | NO |  | FK → user_account.user_id, UQ* | Who wrote it: the application's contributor or the organization's owner (`trg_feedback_*`). |
| `subject_user_id` | `int unsigned` | NO |  | FK → user_account.user_id | Who it is about: the other participant. Not the author (`chk_feedback_not_self`). |
| `rating` | `tinyint unsigned` | NO |  |  | 1 to 5. |
| `comment` | `text` | YES |  |  | Optional text. |
| `created_at` | `datetime` | NO | now |  | When it was written. |

- **Unique:** `uq_feedback_application_author` (application_id, author_user_id)
- **Foreign keys:** `fk_feedback_application` (application_id) → `application` (restrict on delete); `fk_feedback_author` (author_user_id) → `user_account` (restrict on delete); `fk_feedback_subject` (subject_user_id) → `user_account` (restrict on delete)
- **Checks:** `chk_feedback_not_self`, `chk_feedback_rating`
- **Triggers:** `trg_feedback_bi`, `trg_feedback_bu`

### admin_review

An admin's decision on one feedback. No row means the feedback is still pending.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `review_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `feedback_id` | `int unsigned` | NO |  | FK → feedback.feedback_id, UQ | The feedback reviewed. Unique: each feedback is reviewed once. |
| `admin_user_id` | `int unsigned` | NO |  | FK → user_account.user_id | The reviewing admin. Must have role `admin` (`trg_admin_review_*`). |
| `decision` | `enum('approved','rejected')` | NO |  |  | `approved` (counts toward ratings) or `rejected`. |
| `reason` | `varchar(500)` | YES |  |  | Why, especially for a rejection. |
| `reviewed_at` | `datetime` | NO | now |  | When it was reviewed. |

- **Unique:** `uq_admin_review_feedback` (feedback_id)
- **Foreign keys:** `fk_admin_review_admin` (admin_user_id) → `user_account` (restrict on delete); `fk_admin_review_feedback` (feedback_id) → `feedback` (restrict on delete)
- **Triggers:** `trg_admin_review_bi`, `trg_admin_review_bu`

## 6. Rewards (stretch goal)

### badge

Badges contributors can earn, and the points each one is worth.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `badge_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `code` | `varchar(50)` | NO |  | UQ | Stable identifier, e.g. `ten-hours`; unique. |
| `name` | `varchar(100)` | NO |  | UQ | Display name; unique. |
| `description` | `varchar(255)` | YES |  |  | What earns it. |
| `points` | `int unsigned` | NO | `0` |  | Points awarded when earned. |
| `required_verified_hours` | `decimal(6,2)` | YES |  |  | Verified hours needed, for hour-based badges; empty otherwise. |

- **Unique:** `uq_badge_code` (code); `uq_badge_name` (name)

### contributor_badge

Badges a contributor has earned. Each badge is earned once.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `contributor_id` | `int unsigned` | NO |  | PK, FK → contributor_profile.user_id | The contributor. Rows are deleted with the profile. |
| `badge_id` | `int unsigned` | NO |  | PK, FK → badge.badge_id | The badge earned. |
| `awarded_at` | `datetime` | NO | now |  | When it was earned. |

- **Foreign keys:** `fk_contributor_badge_badge` (badge_id) → `badge` (restrict on delete); `fk_contributor_badge_contributor` (contributor_id) → `contributor_profile` (cascade on delete)

### point_transaction

Ledger of points awarded, either for approved work or for a badge. Leaderboard totals are summed from it, never stored.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `transaction_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `contributor_id` | `int unsigned` | NO |  | FK → contributor_profile.user_id, FK → contributor_badge.contributor_id, UQ* | Who receives the points. Must match the verification's or badge's contributor (`trg_point_transaction_*`, `fk_point_transaction_contributor_badge`). |
| `points` | `int` | NO |  |  | Points awarded, as valued at that time. |
| `source` | `enum('work_verified','badge_awarded')` | NO |  |  | `work_verified` or `badge_awarded`; must match which of the next two columns is filled (`chk_point_transaction_source`). |
| `verification_id` | `int unsigned` | YES |  | FK → work_verification.verification_id, UQ | The approved verification, for `work_verified`; unique. |
| `badge_id` | `int unsigned` | YES |  | FK → contributor_badge.badge_id, UQ* | The earned badge, for `badge_awarded`; unique per contributor. |
| `created_at` | `datetime` | NO | now |  | When the points were awarded. |

- **Unique:** `uq_point_transaction_contributor_badge` (contributor_id, badge_id); `uq_point_transaction_verification` (verification_id)
- **Foreign keys:** `fk_point_transaction_contributor` (contributor_id) → `contributor_profile` (restrict on delete); `fk_point_transaction_contributor_badge` (contributor_id, badge_id) → `contributor_badge` (restrict on delete); `fk_point_transaction_verification` (verification_id) → `work_verification` (restrict on delete)
- **Checks:** `chk_point_transaction_source`
- **Triggers:** `trg_point_transaction_bi`, `trg_point_transaction_bu`

## 7. Notifications

### notification

One message per user per event, written by the consumer services and read by the frontend through `/api/v1/notifications` (ADR 0003). Not in the original 17-entity proposal.

| Column | Type | Null | Default | Key | Description |
|---|---|---|---|---|---|
| `notification_id` | `int unsigned` | NO |  | PK | Surrogate key. |
| `user_id` | `int unsigned` | NO |  | FK → user_account.user_id, UQ* | Who receives it. Rows are deleted with the account. |
| `event_id` | `char(36)` | NO |  | UQ* | The RabbitMQ event that caused it (UUID). Unique together with `user_id`, so a redelivered event adds nothing. |
| `notification_type` | `enum('opportunity_created','opportunity_published')` | NO |  |  | `opportunity_created` (to matching contributors) or `opportunity_published` (to the creator). Gains a value per notifying event. |
| `title` | `varchar(200)` | NO |  |  | Headline as shown to the user, stored as written. |
| `message` | `varchar(500)` | NO |  |  | Body as shown to the user, stored as written. |
| `opportunity_id` | `int unsigned` | YES |  | FK → opportunity.opportunity_id | Related opportunity, if any. Set to empty if the opportunity is deleted. |
| `read_at` | `datetime` | YES |  |  | When the user read it; empty means unread. |
| `created_at` | `datetime` | NO | now |  | When it was created. |

- **Unique:** `uq_notification_event_user` (event_id, user_id)
- **Foreign keys:** `fk_notification_opportunity` (opportunity_id) → `opportunity` (set null on delete); `fk_notification_user` (user_id) → `user_account` (cascade on delete)

## 8. Views (derived values)

Totals, ratings and feedback status are never stored (I1, I3). These views compute them from the tables above, so they can't drift out of date. Views are read-only.

### v_contributor_verified_hours

Verified hours and completed opportunities per contributor, summed from approved verifications (0 when none yet).

| Column | Type | Description |
|---|---|---|
| `contributor_id` | `int unsigned` | The contributor. |
| `verified_hours` | `decimal(28,2)` | Sum of `work_verification.verified_hours` for approved work. |
| `completed_opportunities` | `bigint` | Number of approved verifications. |

### v_user_rating

Average rating per user, from admin-approved feedback only.

| Column | Type | Description |
|---|---|---|
| `user_id` | `int unsigned` | The rated user. |
| `average_rating` | `decimal(6,2)` | Average `feedback.rating` over approved feedback; empty with none. |
| `approved_feedback_count` | `bigint` | Number of approved feedback rows. |

### v_leaderboard

Total points and rank per active contributor, summed from `point_transaction` (0 when none yet).

| Column | Type | Description |
|---|---|---|
| `contributor_id` | `int unsigned` | The contributor. |
| `full_name` | `varchar(150)` | From `user_account`. |
| `total_points` | `decimal(32,0)` | Sum of `point_transaction.points`. |
| `leaderboard_rank` | `bigint unsigned` | Rank by total points (ties share a rank). |

### v_feedback_status

Every feedback with its status (`pending`, `approved`, `rejected`) derived from `admin_review`.

| Column | Type | Description |
|---|---|---|
| `feedback_id` | `int unsigned` | The feedback. |
| `application_id` | `int unsigned` | From `feedback`. |
| `author_user_id` | `int unsigned` | From `feedback`. |
| `subject_user_id` | `int unsigned` | From `feedback`. |
| `rating` | `tinyint unsigned` | From `feedback`. |
| `status` | `varchar(8)` | `pending` with no review, otherwise the review's decision. |
| `reviewed_at` | `datetime` | From `admin_review`; empty while pending. |

## 9. Enumerated values

| Column | Allowed values |
|---|---|
| `user_account.role` | `creator`, `contributor`, `admin` |
| `creator_organization.organization_type` | `small_business`, `nonprofit`, `event_organizer`, `other` |
| `opportunity.work_mode` | `on_site`, `remote`, `hybrid` |
| `opportunity.compensation_type` | `paid`, `stipend`, `unpaid` |
| `opportunity.status` | `draft`, `open`, `closed`, `cancelled` |
| `contributor_skill.source` | `self_reported`, `verified` |
| `application.status` | `pending`, `accepted`, `rejected`, `withdrawn` |
| `work_verification.decision` | `approved`, `rejected` |
| `admin_review.decision` | `approved`, `rejected` |
| `point_transaction.source` | `work_verified`, `badge_awarded` |
| `notification.notification_type` | `opportunity_created`, `opportunity_published` |

