# Functional Dependencies — Grow8 Database

**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty

> Based on the ENSF 608 proposal submitted Oct 9, 2026. To be reconciled with the schema once it is committed to the repo.

## 1. Purpose

This document lists the keys and functional dependencies (FDs) for each of the 17 entities, as groundwork for the formal normalization analysis after the Oct 16 lecture. It also flags early risks to 1NF, 2NF and 3NF.

Attributes come from the proposal (section 3). IDs and foreign keys have been added; names are provisional until the logical model is final. Issue codes (I1–I9) refer to `relationship-validation.md`.

## 2. Notation

- **X → Y** — X determines Y (each value of X has exactly one value of Y)
- **PK** — primary key · **CK** — other candidate key · **FK** — foreign key
- A table is in **BCNF** when every determinant (left side of an FD) is a candidate key.

## 3. Entities

### 3.1 UserAccount
`UserAccount(user_id, email, password_hash, account_status, role)`

- **PK:** `user_id` · **CK:** `email`
- **FDs:**
  - `user_id → email, password_hash, account_status, role`
  - `email → user_id`
- **Check:** both determinants are candidate keys → BCNF.
- **Note:** no attribute in the whole proposal stores a person's name. Suggest adding `full_name` here.

### 3.2 ContributorProfile
`ContributorProfile(user_id, biography, interests, availability)`

- **PK:** `user_id` (also FK → UserAccount)
- **FDs:** `user_id → biography, interests, availability`
- **Check:** BCNF, **but 1NF risk.** If `interests` or `availability` hold lists (e.g. "data entry, events"), the table breaks 1NF. Either keep each as a single descriptive text field for the MVP, or move it to its own table (e.g. `ContributorInterest(user_id, category_id)`).

### 3.3 CreatorOrganization
`CreatorOrganization(organization_id, manager_user_id, name, organization_type)`

- **PK:** `organization_id`
- **FDs:** `organization_id → manager_user_id, name, organization_type`
- **Check:** BCNF. Optional `UNIQUE (manager_user_id, name)` to stop one Creator creating duplicate organizations.
- **3NF note:** don't copy the manager's email or role here; they depend on `manager_user_id`, not on the organization (transitive dependency).

### 3.4 OpportunityCategory
`OpportunityCategory(category_id, name, description)`

- **PK:** `category_id` · **CK:** `name`
- **FDs:**
  - `category_id → name, description`
  - `name → category_id`
- **Check:** BCNF.

### 3.5 Opportunity
`Opportunity(opportunity_id, organization_id, category_id, title, task_details, expected_hours, compensation, working_conditions, safety_info, accessibility_info, deadline, applicant_limit, status)`

- **PK:** `opportunity_id`
- **FDs:** `opportunity_id → all other attributes`
- **Check:**
  - **2NF:** single-column PK, so no partial dependencies.
  - **3NF risk:** store only `organization_id` and `category_id`. Copying the organization name or category name here would create `opportunity_id → organization_id → name` (transitive).
  - **1NF risk:** `compensation` should be atomic — e.g. an amount column plus a unit/type column — not one free-text value. If `safety_info` or `accessibility_info` become checklists of several items, they need their own tables.
  - **Derived data:** don't store the number of applicants; calculate it from Application.

### 3.6 Skill
`Skill(skill_id, name, description)`

- **PK:** `skill_id` · **CK:** `name`
- **FDs:**
  - `skill_id → name, description`
  - `name → skill_id`
- **Check:** BCNF.

### 3.7 ContributorSkill
`ContributorSkill(contributor_id, skill_id, proficiency, verification_status)`

- **PK:** `(contributor_id, skill_id)`
- **FDs:** `(contributor_id, skill_id) → proficiency, verification_status`
- **2NF check:** no attribute depends on only part of the key → 2NF. Adding `skill_name` here would break 2NF (`skill_id → skill_name` is a partial dependency).
- **Note:** if "verified" means the skill was used in approved work, `verification_status` is derivable and could be a view instead of a stored column.

### 3.8 OpportunitySkill
`OpportunitySkill(opportunity_id, skill_id, requirement_type)`

- **PK:** `(opportunity_id, skill_id)`
- **FDs:** `(opportunity_id, skill_id) → requirement_type`
- **2NF check:** full-key dependency only → 2NF. Don't add `skill_name` or the opportunity title.

### 3.9 Application
`Application(application_id, contributor_id, opportunity_id, applied_date, status)`

- **PK:** `application_id` · **CK:** `(contributor_id, opportunity_id)`
- **FDs:**
  - `application_id → contributor_id, opportunity_id, applied_date, status`
  - `(contributor_id, opportunity_id) → application_id`
- **Check:** both determinants are candidate keys → BCNF. The CK is what prevents duplicate applications.

### 3.10 WorkSubmission
`WorkSubmission(submission_id, application_id, completion_notes, submitted_date)`

- **PK:** `submission_id` · **CK:** `application_id` (1 : 0..1)
- **FDs:**
  - `submission_id → application_id, completion_notes, submitted_date`
  - `application_id → submission_id`
- **Check:** BCNF.
- **3NF note:** don't store `contributor_id` or `opportunity_id` here; both are reachable through `application_id`.

### 3.11 SubmissionAttachment
`SubmissionAttachment(attachment_id, submission_id, file_name, mime_type, storage_key, uploaded_date)`

- **PK:** `attachment_id` · **CK:** `storage_key`
- **FDs:**
  - `attachment_id → submission_id, file_name, mime_type, storage_key, uploaded_date`
  - `storage_key → attachment_id`
- **Check:** BCNF.

### 3.12 WorkVerification
`WorkVerification(verification_id, submission_id, verified_by_user_id, decision, decision_date, approved_hours)`

- **PK:** `verification_id` · **CK:** `submission_id` (1 : 0..1)
- **FDs:**
  - `verification_id → submission_id, verified_by_user_id, decision, decision_date, approved_hours`
  - `submission_id → verification_id`
- **Check:** BCNF.
- **Notes:**
  - `verified_by_user_id` is proposed (R20). It is not redundant: it records who verified at that time, which can differ from the organization's current manager.
  - `approved_hours` being set only for approved decisions is a business rule (`CHECK`), not an FD problem.

### 3.13 Feedback
`Feedback(feedback_id, application_id, author_user_id, recipient_user_id, rating, comments, feedback_date, approval_status)`

- **PK:** `feedback_id`
- **FDs:** `feedback_id → all other attributes`
- **Check:** BCNF within the table, but two cross-table redundancies:
  - **`approval_status`** duplicates `AdminReview.decision` → remove it and derive it (I1).
  - **`author_user_id` / `recipient_user_id`** are partly determined by `application_id` (the application fixes who the Contributor and Creator are). Kept on purpose for simpler queries, with a participant check (I2).
- **Constraint:** `rating` within a fixed range, e.g. `CHECK (rating BETWEEN 1 AND 5)`.

### 3.14 AdminReview
`AdminReview(review_id, feedback_id, reviewer_user_id, review_date, findings, decision)`

- **PK:** `review_id` · **CK:** `feedback_id` (1 : 0..1)
- **FDs:**
  - `review_id → feedback_id, reviewer_user_id, review_date, findings, decision`
  - `feedback_id → review_id`
- **Check:** BCNF.

### 3.15 Badge
`Badge(badge_id, name, description, earning_criteria, point_value)`

- **PK:** `badge_id` · **CK:** `name`
- **FDs:**
  - `badge_id → name, description, earning_criteria, point_value`
  - `name → badge_id`
- **Check:** BCNF.

### 3.16 ContributorBadge
`ContributorBadge(contributor_badge_id, contributor_id, badge_id, earned_date)`

- **PK:** `contributor_badge_id` (surrogate, because PointTransaction references it)
- **CK:** `(contributor_id, badge_id)` — only if a badge can be earned once (I9)
- **FDs:**
  - `contributor_badge_id → contributor_id, badge_id, earned_date`
  - `(contributor_id, badge_id) → contributor_badge_id` (if once only)
- **Check:** BCNF.
- **3NF note:** don't copy `point_value` here; it depends on `badge_id`.

### 3.17 PointTransaction
`PointTransaction(transaction_id, contributor_id, amount, reason, transaction_date, verification_id, contributor_badge_id)`

- **PK:** `transaction_id`
- **CK:** `verification_id`, `contributor_badge_id` — each unique when filled, exactly one filled per row (I5)
- **FDs:**
  - `transaction_id → contributor_id, amount, reason, transaction_date, verification_id, contributor_badge_id`
  - `verification_id → transaction_id` (when not null)
  - `contributor_badge_id → transaction_id` (when not null)
- **Check:** BCNF within the table. Two cross-table redundancies, both **accepted on purpose**:
  - **`contributor_id`** is reachable through either source. Kept so leaderboard totals don't need four joins.
  - **`amount`** for badge points equals `Badge.point_value`. Kept because a ledger records the value awarded *at that time*; a badge's point value could change later.

## 4. Preliminary findings

| Entity | Status | Action |
|---|---|---|
| UserAccount | BCNF | Add `full_name` |
| ContributorProfile | 1NF risk | Keep `interests` / `availability` atomic or move to a table |
| CreatorOrganization | BCNF | Don't copy manager details |
| OpportunityCategory | BCNF | — |
| Opportunity | 1NF / 3NF risk | Atomic compensation; no copied names; calculate applicant count |
| Skill | BCNF | — |
| ContributorSkill | 2NF OK | Don't add `skill_name`; consider deriving `verification_status` |
| OpportunitySkill | 2NF OK | Don't add `skill_name` |
| Application | BCNF | Keep `(contributor_id, opportunity_id)` unique |
| WorkSubmission | BCNF | Don't copy contributor / opportunity IDs |
| SubmissionAttachment | BCNF | — |
| WorkVerification | BCNF | Add `verified_by_user_id` |
| Feedback | Cross-table redundancy | Remove `approval_status` (I1) |
| AdminReview | BCNF | — |
| Badge | BCNF | — |
| ContributorBadge | BCNF | Don't copy `point_value` |
| PointTransaction | Accepted redundancy | Document; set consistently in backend |

## 5. Next steps

- After the Oct 16 lecture: confirm each table's normal form formally and decompose anything that fails.
- Reconcile attribute names with the logical model and the schema DDL once they are in the repo.
