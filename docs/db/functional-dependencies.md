# Functional Dependencies and Normalization — Grow8 Database

**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty

> Updated Oct 23, 2026 against the committed schema, `grow8-backend/db/init/001_schema.sql`, and on Oct 27 for the `notification` table (ADR 0003). The first version (Oct 14) analysed the proposal's preliminary entities; section 6 lists what changed between the two. Issue codes (I1–I9, R1–R22) refer to `relationship-validation.md`; column-level details are in `data-dictionary.md`.

## 1. Purpose

For each of the 18 tables (the 17 from the proposal plus `notification`) this document gives the keys and the functional dependencies (FDs), then checks the table against 1NF, 2NF, 3NF and BCNF. Section 4 covers redundancy *between* tables, which per-table normalization does not catch, and how each case is either removed or enforced.

**Result:** all 18 tables are in BCNF. Every derived total is calculated by a view instead of being stored, and the few cross-table redundancies kept on purpose are each enforced by a constraint or trigger.

## 2. Notation and method

- **X → Y**: X determines Y (each value of X has exactly one value of Y).
- **PK**: primary key · **CK**: other candidate key · **FK**: foreign key.
- **1NF**: every attribute is atomic (no lists or repeating groups) and the table has a key.
- **2NF**: 1NF, and no non-prime attribute depends on only part of a candidate key.
- **3NF**: 2NF, and no non-prime attribute depends on another non-prime attribute (no transitive dependency).
- **BCNF**: the left side of every non-trivial FD is a superkey. BCNF implies 3NF and 2NF.

Method for each table: list every FD that holds *within* the table, find the candidate keys, and check that every determinant is a superkey.

**Nullable unique columns.** `point_transaction.verification_id` and `(point_transaction.contributor_id, badge_id)` are unique only where they are filled (MySQL allows several NULLs in a unique index). They are treated as candidate keys of the rows where they are not null; this does not change any result below.

**Audit columns.** `created_at`, `updated_at`, `published_at`, `submitted_at` and similar timestamps depend only on the table's key. They are listed as "timestamps" to keep the FDs readable.

## 3. Tables

### 3.1 user_account
`user_account(user_id, email, password_hash, role, full_name, is_active, timestamps)`

- **PK** `user_id` · **CK** `email` (`uq_user_account_email`)
- **FDs:** `user_id → email, password_hash, role, full_name, is_active, timestamps`; `email → user_id`
- **Normal form:** both determinants are candidate keys → **BCNF**.

### 3.2 contributor_profile
`contributor_profile(user_id, headline, bio, institution, city, timestamps)`

- **PK** `user_id` (also FK → user_account, shared-PK 1 : 0..1, R1)
- **FDs:** `user_id → headline, bio, institution, city, timestamps`
- **Normal form:** **BCNF**. The proposal's 1NF risk (list-valued `interests`, `availability`) is gone: interests are rows in `contributor_skill`, and availability was dropped from the MVP.

### 3.3 creator_organization
`creator_organization(organization_id, owner_user_id, name, organization_type, description, website, city, timestamps)`

- **PK** `organization_id` · **CK** `owner_user_id` (`uq_creator_organization_owner`: one organization per creator in the MVP)
- **FDs:** `organization_id → owner_user_id, name, organization_type, description, website, city, timestamps`; `owner_user_id → organization_id`
- **Normal form:** **BCNF**. No owner details (email, name) are copied here, so there is no transitive dependency through `owner_user_id`.

### 3.4 opportunity_category
`opportunity_category(category_id, code, name, description)`

- **PK** `category_id` · **CK** `code`, `name`
- **FDs:** `category_id → code, name, description`; `code → category_id`; `name → category_id`
- **Normal form:** **BCNF**.

### 3.5 skill
`skill(skill_id, code, name)`

- **PK** `skill_id` · **CK** `code`, `name`
- **FDs:** `skill_id → code, name`; `code → skill_id`; `name → skill_id`
- **Normal form:** **BCNF**.

### 3.6 opportunity
`opportunity(opportunity_id, organization_id, category_id, title, description, requirements, location, work_mode, start_date, end_date, expected_hours, compensation_type, compensation_amount, compensation_details, applicant_limit, application_deadline, working_conditions, safety_information, accessibility_details, status, timestamps)`

- **PK** `opportunity_id`
- **FDs:** `opportunity_id → every other attribute`. No other attribute or combination determines anything: several opportunities can share a title, organization, category, compensation type, status and dates.
- **Normal form:** **BCNF**.
- **Checks from the proposal stage:**
  - **1NF:** compensation is atomic: a type (`paid` / `stipend` / `unpaid`), an amount and free-text details, instead of one free-text value. Safety and accessibility information are single descriptive fields, not checklists.
  - **3NF:** only `organization_id` and `category_id` are stored, never the organization or category name, so there is no `opportunity_id → organization_id → name` chain.
  - **Derived data:** the number of applicants is not stored; it is counted from `application`.
- **Business rule, not an FD:** `chk_opportunity_published_complete` requires every mandatory disclosure once the status leaves `draft`.

### 3.7 opportunity_skill
`opportunity_skill(opportunity_id, skill_id)`

- **PK** `(opportunity_id, skill_id)`
- **FDs:** only trivial ones (the table is all key).
- **Normal form:** **BCNF**. No skill name or opportunity title is copied in, which would have created a partial dependency (`skill_id → name`).

### 3.8 contributor_skill
`contributor_skill(contributor_id, skill_id, source, created_at)`

- **PK** `(contributor_id, skill_id)`
- **FDs:** `(contributor_id, skill_id) → source, created_at`
- **2NF:** neither `contributor_id` nor `skill_id` alone determines `source` or `created_at` → no partial dependency.
- **Normal form:** **BCNF**.
- **Open point:** see decision 7 in section 5 about whether `source = 'verified'` is stored or derived.

### 3.9 application
`application(application_id, opportunity_id, contributor_id, status, motivation, submitted_at, decided_at)`

- **PK** `application_id` · **CK** `(contributor_id, opportunity_id)` (`uq_application_contributor_opportunity`)
- **FDs:** `application_id → opportunity_id, contributor_id, status, motivation, submitted_at, decided_at`; `(contributor_id, opportunity_id) → application_id`
- **2NF:** no non-prime attribute depends on `contributor_id` or `opportunity_id` alone.
- **Normal form:** **BCNF**. The second candidate key is what stops duplicate applications.

### 3.10 work_submission
`work_submission(submission_id, application_id, description, hours_claimed, submitted_at)`

- **PK** `submission_id` · **CK** `application_id` (`uq_work_submission_application`, the 1 : 0..1 of R9)
- **FDs:** `submission_id → application_id, description, hours_claimed, submitted_at`; `application_id → submission_id`
- **Normal form:** **BCNF**. The contributor and opportunity are not copied here; both are reached through `application_id`.

### 3.11 submission_attachment
`submission_attachment(attachment_id, submission_id, file_name, content_type, size_bytes, storage_key, uploaded_at)`

- **PK** `attachment_id` · **CK** `storage_key`
- **FDs:** `attachment_id → submission_id, file_name, content_type, size_bytes, storage_key, uploaded_at`; `storage_key → attachment_id`
- **Normal form:** **BCNF**.

### 3.12 work_verification
`work_verification(verification_id, submission_id, verified_by_user_id, decision, verified_hours, comment, verified_at)`

- **PK** `verification_id` · **CK** `submission_id` (`uq_work_verification_submission`, the 1 : 0..1 of R11)
- **FDs:** `verification_id → submission_id, verified_by_user_id, decision, verified_hours, comment, verified_at`; `submission_id → verification_id`
- **Normal form:** **BCNF**.
- **Notes:**
  - `verified_by_user_id` (R20) is a historical fact: who verified at the time. It can't be derived from the organization's *current* owner.
  - "`verified_hours` only when approved" is a business rule (`chk_work_verification_hours`), not an FD.

### 3.13 feedback
`feedback(feedback_id, application_id, author_user_id, subject_user_id, rating, comment, created_at)`

- **PK** `feedback_id` · **CK** `(application_id, author_user_id)` (`uq_feedback_application_author`)
- **FDs:**
  - `feedback_id → application_id, author_user_id, subject_user_id, rating, comment, created_at`
  - `(application_id, author_user_id) → feedback_id`
  - `(application_id, author_user_id) → subject_user_id`, and `(application_id, subject_user_id) → author_user_id`: an application has exactly two participants, so knowing one fixes the other.
- **Normal form:** **BCNF**. Both left sides are candidate keys. `(application_id, subject_user_id)` is also a candidate key implicitly, since it determines the author.
- **Approval status is not stored here** (I1); it is derived in `v_feedback_status`.

### 3.14 admin_review
`admin_review(review_id, feedback_id, admin_user_id, decision, reason, reviewed_at)`

- **PK** `review_id` · **CK** `feedback_id` (`uq_admin_review_feedback`)
- **FDs:** `review_id → feedback_id, admin_user_id, decision, reason, reviewed_at`; `feedback_id → review_id`
- **Normal form:** **BCNF**.

### 3.15 badge
`badge(badge_id, code, name, description, points, required_verified_hours)`

- **PK** `badge_id` · **CK** `code`, `name`
- **FDs:** `badge_id → code, name, description, points, required_verified_hours`; `code → badge_id`; `name → badge_id`
- **Normal form:** **BCNF**.

### 3.16 contributor_badge
`contributor_badge(contributor_id, badge_id, awarded_at)`

- **PK** `(contributor_id, badge_id)`, so each badge can be earned once (I9)
- **FDs:** `(contributor_id, badge_id) → awarded_at`
- **Normal form:** **BCNF**. `points` is not copied here; it depends on `badge_id` alone, which would be a partial dependency.

### 3.17 point_transaction
`point_transaction(transaction_id, contributor_id, points, source, verification_id, badge_id, created_at)`

- **PK** `transaction_id` · **CK** `verification_id` (where filled) · **CK** `(contributor_id, badge_id)` (where `badge_id` is filled)
- **FDs:** `transaction_id → contributor_id, points, source, verification_id, badge_id, created_at`; `verification_id → transaction_id`; `(contributor_id, badge_id) → transaction_id`
- **Normal form:** **BCNF** within the table.
- **`source`** is redundant with "which of `verification_id` / `badge_id` is filled". `chk_point_transaction_source` keeps them consistent, and the column is kept so ledger queries read clearly.

### 3.18 notification
`notification(notification_id, user_id, event_id, notification_type, title, message, opportunity_id, read_at, created_at)`

Added Oct 27 (ADR 0003); not in the proposal. One row per user per event.

- **PK** `notification_id` · **CK** `(event_id, user_id)` (`uq_notification_event_user`: a redelivered event adds nothing)
- **FDs:** `notification_id → user_id, event_id, notification_type, title, message, opportunity_id, read_at, created_at`; `(event_id, user_id) → notification_id`
- **Not an FD:** `opportunity_id ↛ title, message`. The text is stored as it was shown, like a sent email, so it can differ from the opportunity's current title. `event_id ↛ notification_type` either: one `OPPORTUNITY_CREATED` event gives contributors an `opportunity_created` row and the creator an `opportunity_published` row.
- **Normal form:** both determinants are candidate keys → **BCNF**.

## 4. Redundancy between tables

Normalization works one table at a time, so it does not catch a fact that is stored in one table and also reachable through others. Each such case is listed here with its treatment.

| Fact | Where it could be duplicated | Treatment |
|---|---|---|
| Contributor's verified hours | a stored total | **Removed.** `v_contributor_verified_hours` sums approved verifications (I3). |
| Public rating | a stored average | **Removed.** `v_user_rating` averages admin-approved feedback only (I3). |
| Leaderboard total | a stored total | **Removed.** `v_leaderboard` sums `point_transaction` (I3). |
| Feedback approval status | `feedback.approval_status` and `admin_review.decision` | **Removed** from `feedback`; `v_feedback_status` derives it (I1). |
| Feedback participants | `feedback.author_user_id` / `subject_user_id` and the application's contributor and organization owner | **Kept** for simpler rating and moderation queries; enforced by `trg_feedback_bi/bu` (I2). |
| Contributor of a verification point | `point_transaction.contributor_id` and verification → submission → application | **Kept** so the leaderboard needs no four-table join; enforced by `trg_point_transaction_bi/bu` (I3). |
| Contributor of a badge point | `point_transaction.(contributor_id, badge_id)` and `contributor_badge` | **Kept**; enforced by `fk_point_transaction_contributor_badge`. |
| Badge point value | `point_transaction.points` and `badge.points` | **Not redundant.** The ledger records the value awarded at that time, and a badge's value may change later. |
| Verifier | `work_verification.verified_by_user_id` and the organization's owner | **Not redundant.** Historical fact (R20). `trg_work_verification_bi/bu` checks it was the owner at the time. |
| Notification text | `notification.title`, `message` and the linked opportunity's title and deadline | **Not redundant.** A record of what the user was told at that time; the opportunity may change later (R22). |
| Read state | `notification.read_at` | **Single source.** The unread count is `COUNT(*) WHERE read_at IS NULL`, never stored. |

## 5. Decisions

Decisions 1–6 were open in the first version; the committed schema settles them.

| # | Decision | Outcome in the schema |
|---|---|---|
| 1 | Stored vs calculated totals | **Calculated** (views; see section 4). |
| 2 | Rating target | The subject **user**. While each creator owns one organization (`uq_creator_organization_owner`), this is the same as rating the organization. If creators may own several later, rate the organization, which is derivable through application → opportunity. |
| 3 | One role per account | **Yes** (`user_account.role`). A role is locked once role-specific rows exist (`trg_user_account_bu`). |
| 4 | Applicant limit counts all or only accepted applications | **Still open.** To be enforced in the backend apply endpoint (not built yet) with `SELECT … FOR UPDATE` on the opportunity row. |
| 5 | Badge repeatable | **Once only** (composite PK of `contributor_badge`). |
| 6 | Feedback per application | **One per author** (`uq_feedback_application_author`). |
| 7 | *New:* `contributor_skill.source = 'verified'` | **Open.** If it means "the skill was used in approved work", it is derivable and should be a view. If it means "the creator confirmed the skill" during verification, it is a stored fact; record who confirmed it. Decide before building `WORK_VERIFIED`. |

## 6. Changes since the proposal-stage analysis (Oct 14)

| Proposal entity / attribute | Committed schema |
|---|---|
| `UserAccount.account_status` | `user_account.is_active`; `full_name` added as recommended. |
| `ContributorProfile.interests`, `availability` | Replaced by `contributor_skill`; availability dropped (removes the 1NF risk). |
| `CreatorOrganization.manager_user_id` | `owner_user_id`, unique (one organization per creator). |
| `Opportunity.compensation` | Split into `compensation_type`, `compensation_amount`, `compensation_details` (atomic). |
| `OpportunitySkill.requirement_type` | Dropped (all listed skills are relevant). |
| `ContributorSkill.proficiency`, `verification_status` | `source` (`self_reported` / `verified`). |
| `WorkVerification.approved_hours` | `verified_hours`; `verified_by_user_id` added (R20). |
| `Feedback.recipient_user_id`, `approval_status` | `subject_user_id`; `approval_status` removed (I1). |
| `AdminReview.reviewer_user_id`, `findings` | `admin_user_id`, `reason`. |
| `ContributorBadge.contributor_badge_id` | Dropped; composite PK `(contributor_id, badge_id)`. |
| `PointTransaction.contributor_badge_id`, `amount`, `reason` | `(contributor_id, badge_id)` referencing `contributor_badge`, `points`, `source`. |
| *(none; Notification was dropped at proposal stage)* | `notification` added Oct 27 (ADR 0003) so users can see what the consumers tell them. |
