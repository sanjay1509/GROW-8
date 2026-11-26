# Normalization to 3NF — Grow8 Database

**ENSF 608 · Group 2 · Final artifact: Normalization**

## 1. Result

The final logical model has **21 relations, and every one is in 3NF**. In fact every one is also in BCNF: in each relation, every non-trivial functional dependency (FD) has a candidate key on its left side.

This document covers only the places where a normalization issue existed in the preliminary design (the Oct 9 proposal) or where a design choice had to be made. Relations whose only dependencies are on their key are listed in the summary table in section 4 rather than worked through one by one.

- The full per-relation FD listing is kept in the repository as a reference: `docs/db/functional-dependencies.md`.
- The SQL that implements the result is `04-implementation/01_create_schema.sql`.

## 2. Method

For each relation we listed its FDs, found its candidate keys, and checked three normal forms:

- **1NF:** every attribute is atomic (no lists or repeating groups) and the relation has a key.
- **2NF:** no non-key attribute depends on only part of a composite key (no partial dependency).
- **3NF:** no non-key attribute depends on another non-key attribute (no transitive dependency).

Normalizing one relation at a time does not catch a fact that is stored in one relation and can also be worked out from others, such as a stored total. We checked those cases separately (decisions N6, N9 and N10).

## 3. Normalization decisions

### N1 — 1NF: multi-valued skills and interests

- **Preliminary design:** `ContributorProfile.interests` and `availability` were list-valued, with several values in one attribute.
- **Problem:**
  - A list attribute is not atomic, so the relation is not in 1NF.
  - "Which contributors have skill X?" would need string parsing.
  - Renaming a skill would mean editing every string that contains it (an update anomaly).
- **Decision:**
  - Skills became a reference relation, `skill(skill_id, code, name)`.
  - Two junction relations link to it:
    - `contributor_skill(contributor_id, skill_id, created_at)`
    - `opportunity_skill(opportunity_id, skill_id)`
  - `availability` was removed from the MVP.
- **Result:**
  - All attributes are atomic.
  - The composite primary keys stop the same skill being listed twice.
  - A skill name is stored exactly once.

### N2 — 1NF: non-atomic compensation

- **Preliminary design:** `Opportunity.compensation` was one free-text value, for example "$100 stipend paid after delivery".
- **Problem:** it combined three facts (the kind of payment, the amount and the conditions). The database could not filter or check them.
- **Decision:** split into three columns:
  - `compensation_type ENUM('paid','stipend','unpaid')`
  - `compensation_amount DECIMAL(10,2)`
  - `compensation_details`
- **Result:** each attribute is atomic. The database can now enforce `chk_opportunity_published_complete`: a published opportunity must state its compensation type, and must state an amount unless it is unpaid.

### N3 — 2NF: no attributes of the referenced entity in junction relations

- **Risk:** the relations with composite keys are `opportunity_skill`, `contributor_skill` and `contributor_badge`. Copying a convenient attribute into them would create a partial dependency. Two examples:
  - the skill name in `opportunity_skill`, where `skill_id → name` depends on only part of the key `(opportunity_id, skill_id)`;
  - the badge points in `contributor_badge`, where `badge_id → points` depends on only part of `(contributor_id, badge_id)`.
- **Decision:** junction relations hold only their key, plus the time the fact was recorded (`created_at`, `awarded_at`), which depends on the whole key.
- **Result:** no partial dependencies anywhere in the model.

### N4 — 3NF: no transitive dependencies through foreign keys

- **Risk:** storing descriptive attributes of a referenced row creates a chain of the form `key → foreign key → attribute`. Examples:
  - an organization's name or city in `opportunity` (`opportunity_id → organization_id → name`);
  - the contributor or opportunity in `work_submission` (`submission_id → application_id → contributor_id`).
- **Decision:** each relation stores only the foreign key, and descriptive data is reached by a join. In particular:
  - `work_submission` stores only `application_id`;
  - `work_verification` stores only `submission_id`;
  - `opportunity` stores only `organization_id` and `category_id`.
- **Result:** no non-key attribute depends on another non-key attribute.

### N5 — Redundant approval status: feedback and reports

- **Preliminary design:** `Feedback.approval_status` was stored in `feedback`, and the admin's decision was stored again in `AdminReview.decision`.
- **Problem:**
  - The status is a fact about the review, not about the feedback.
  - Storing it twice allows contradictions, such as feedback marked "approved" whose review says "rejected".
  - Every review would need two updates kept in step (an update anomaly).
- **Decision:**
  - `approval_status` was removed from `feedback`.
  - The view `v_feedback_status` derives the status as `COALESCE(admin_review.decision, 'pending')`.
  - The same pattern is used for opportunity reports: a report with no `report_review` row is pending.
  - Whether an opportunity was taken down is not stored on `opportunity`. It is a cancelled opportunity with an upheld report.
- **Result:** each decision is stored once, in the relation that records it.

### N6 — Derived totals are calculated, not stored

- **Risk:** totals such as a contributor's verified hours, a creator's rating, leaderboard points or the places taken on an opportunity depend on rows in other relations. A stored total is wrong as soon as one update path forgets to change it.
- **Decision:** every total is calculated from the underlying rows:

| Value | Calculated by |
|---|---|
| Verified hours and completed opportunities | `v_contributor_verified_hours` (approved verifications only) |
| Public rating | `v_user_rating` (admin-approved feedback only) |
| Leaderboard total and rank | `v_leaderboard` (sum of the `point_transaction` ledger) |
| Places taken on an opportunity | counted inside `grow8_require_application_capacity` while the opportunity row is locked |
| Unread notifications | `COUNT(*) … WHERE read_at IS NULL` |

- **Result:** no stored value can drift from the rows it summarizes.

### N7 — The "verified" skill flag is derived

- **Preliminary design:** `ContributorSkill.verification_status` (later a `source` column) recorded whether a skill was verified.
- **Problem:** "verified" means the skill was required by an opportunity where the contributor's work was approved. That depends on `application`, `work_verification` and `opportunity_skill`, not on the key of `contributor_skill`. Storing it creates a dependency on other relations that can go stale.
- **Decision:**
  - The column was dropped, and the view `v_contributor_skill` derives `is_verified` and `verified_at`.
  - The view also covers skills earned through approved work that the contributor never listed.
  - `contributor_skill` holds only what the contributor chose to list.
- **Result:** `contributor_skill` is all key plus `created_at`, which puts it in BCNF.

### N8 — An optional group of attributes gets its own relation

- **Issue:** a contributor's optional resume has five attributes (file name, type, size, storage key, upload time). As columns on `contributor_profile` they would be NULL together for most contributors, and a CHECK would be needed to keep them all-or-nothing.
- **Decision:** a 1 : 0..1 relation, `contributor_resume(user_id PK/FK, file_name, content_type, size_bytes, storage_key, uploaded_at)`, with `storage_key` as a second candidate key.
- **Result:** no NULL groups, and `contributor_profile` keeps its simple dependencies.

### N9 — Controlled redundancy kept on purpose, and how it is protected

Three cross-relation redundancies were kept for query simplicity. None of them breaks 3NF inside its own relation. Each one is enforced by the database so it cannot become inconsistent.

| Redundant fact | Why it is kept | Enforced by |
|---|---|---|
| `feedback.author_user_id` / `subject_user_id` (also reachable through the application and the organization owner) | Ratings and moderation queries need no four-table join | `trg_feedback_bi/bu`: author and subject must be the application's contributor and the organization's owner |
| `point_transaction.contributor_id` for verification points (also reachable through verification → submission → application) | The leaderboard reads one table | `trg_point_transaction_bi/bu`: the verification must be approved and belong to the same contributor |
| `point_transaction.(contributor_id, badge_id)` for badge points | Same | Composite FK `fk_point_transaction_contributor_badge` to `contributor_badge`: badge points only for a badge actually earned |
| `point_transaction.source` (implied by which of `verification_id` / `badge_id` is filled) | Ledger queries read clearly | `chk_point_transaction_source` |

### N10 — Attributes that look redundant but are historical facts

Each of these attributes records a value **as it was at a moment in time**. Replacing it with a join to the current row would change history, so none of them is a redundant copy:

- `point_transaction.points` is the value awarded at the time; `badge.points` may change later.
- `work_verification.verified_by_user_id` is who verified the work; the organization's owner could change.
- `notification.title` and `message` are what the user was told, like a sent email; the opportunity's title can be edited afterwards.
- `application.resume_*` describes the copy of the resume sent with the application; the profile resume in `contributor_resume` can be replaced independently.

## 4. Summary of all relations

CK = candidate key other than the primary key. Relations marked "key only" have no FD apart from the key determining the other attributes, so they need no separate demonstration.

| Relation | Primary key | Other candidate keys | Notes | Normal form |
|---|---|---|---|---|
| user_account | user_id | email | key only | BCNF |
| contributor_profile | user_id | — | key only (N1) | BCNF |
| contributor_resume | user_id | storage_key | N8 | BCNF |
| creator_organization | organization_id | owner_user_id | key only | BCNF |
| opportunity_category | category_id | code, name | key only | BCNF |
| skill | skill_id | code, name | N1 | BCNF |
| opportunity | opportunity_id | — | N2, N4 | BCNF |
| opportunity_skill | (opportunity_id, skill_id) | — | all key (N1, N3) | BCNF |
| contributor_skill | (contributor_id, skill_id) | — | N1, N3, N7 | BCNF |
| application | application_id | (contributor_id, opportunity_id) | N4, N10 | BCNF |
| work_submission | submission_id | application_id | N4 | BCNF |
| submission_attachment | attachment_id | storage_key | key only | BCNF |
| work_verification | verification_id | submission_id | N4, N10 | BCNF |
| feedback | feedback_id | (application_id, author_user_id) | N5, N9 | BCNF |
| admin_review | review_id | feedback_id | N5 | BCNF |
| opportunity_report | report_id | (opportunity_id, reporter_user_id) | N5 | BCNF |
| report_review | review_id | report_id | N5 | BCNF |
| badge | badge_id | code, name | key only | BCNF |
| contributor_badge | (contributor_id, badge_id) | — | N3 | BCNF |
| point_transaction | transaction_id | verification_id; (contributor_id, badge_id), where filled | N6, N9, N10 | BCNF |
| notification | notification_id | (event_id, user_id) | N10 | BCNF |

## 5. From the preliminary design to the final model

| Preliminary design (Oct 9 proposal) | Final model | Decision |
|---|---|---|
| `ContributorProfile.interests`, `availability` (lists) | `contributor_skill` junction relation; availability dropped | N1 |
| `Opportunity.compensation` (free text) | `compensation_type`, `compensation_amount`, `compensation_details` | N2 |
| `ContributorSkill.proficiency`, `verification_status` | Dropped; verification derived in `v_contributor_skill` | N7 |
| `Feedback.approval_status` | Removed; derived in `v_feedback_status` | N5 |
| Stored totals (hours, rating, points) | Views | N6 |
| `ContributorBadge.contributor_badge_id` (surrogate key) | Composite key `(contributor_id, badge_id)`, so a badge is earned once | N3 |
| `PointTransaction.contributor_badge_id` | Composite FK `(contributor_id, badge_id)` to `contributor_badge` | N9 |
| `CreatorOrganization.manager_user_id` | `owner_user_id`, unique (one organization per creator) | — |
| *(not in proposal)* | `contributor_resume`, `notification`, `opportunity_report`, `report_review` added during implementation, each checked to BCNF | N5, N8, N10 |
