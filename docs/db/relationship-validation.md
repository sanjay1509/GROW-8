# Relationship Validation — Grow8 Database

**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty

> Based on the ENSF 608 proposal submitted Oct 9, 2026. To be reconciled with the schema once it is committed to the repo.

## 1. Purpose

This document checks each of the 19 relationships in the proposal before the schema is written, so that the schema enforces the business rules from the start instead of patching them later.

## 2. Method

For each relationship I checked five things:

1. **Cardinality** — does it match the business rules in proposal sections 1–2?
2. **Foreign key placement** — which table holds the FK, and is it `NOT NULL`?
3. **Maximum of 1** — for every `0..1` side, is there a `UNIQUE` key or shared primary key? Without one, a 1 : 0..1 relationship silently becomes 1 : M.
4. **Redundant paths** — is the same fact stored in two places, or reachable two ways?
5. **Rules a FK cannot enforce** — role checks, status checks and cross-table conditions that need a `CHECK`, a trigger or backend validation.

**Status legend:** ✅ Valid as proposed · ⚠️ Valid, but needs an added constraint · ❌ Needs to change

## 3. Relationship-by-relationship review

| # | Relationship | Card. | Status | Implementation | Notes / issue |
|---|---|---|---|---|---|
| R1 | UserAccount — ContributorProfile | 1 : 0..1 | ⚠️ | `ContributorProfile.user_id` is both PK and FK → UserAccount (shared PK) | Shared PK enforces "at most one profile". Only `role = Contributor` accounts should have one — see I6. |
| R2 | UserAccount — CreatorOrganization | 1 : 0..M | ⚠️ | `CreatorOrganization.manager_user_id` FK, `NOT NULL` | Manager must have `role = Creator` (I6). Raises the rating-target question (I4). |
| R3 | CreatorOrganization — Opportunity | 1 : 0..M | ✅ | `Opportunity.organization_id` FK, `NOT NULL` | Store only the ID; never copy the organization name into Opportunity. |
| R4 | OpportunityCategory — Opportunity | 1 : 0..M | ✅ | `Opportunity.category_id` FK, `NOT NULL` | Store only the ID; never copy the category name. |
| R5 | ContributorProfile — Skill (via ContributorSkill) | M : N | ✅ | ContributorSkill PK `(contributor_id, skill_id)` | Composite PK prevents duplicate skills per Contributor. |
| R6 | Opportunity — Skill (via OpportunitySkill) | M : N | ✅ | OpportunitySkill PK `(opportunity_id, skill_id)`; `requirement_type ENUM('required','preferred')` | — |
| R7 | ContributorProfile — Application | 1 : 0..M | ✅ | `Application.contributor_id` FK, `NOT NULL` | With R8: `UNIQUE (contributor_id, opportunity_id)` prevents duplicate applications, as the proposal states. |
| R8 | Opportunity — Application | 1 : 0..M | ⚠️ | `Application.opportunity_id` FK, `NOT NULL` | Deadline and applicant-limit checks can't be done by a FK (I7). Don't store a running applicant count; calculate it. |
| R9 | Application — WorkSubmission | 1 : 0..1 | ⚠️ | `WorkSubmission.application_id` FK + `UNIQUE` | `UNIQUE` enforces the 0..1. Only *accepted* applications may have a submission (I7). |
| R10 | WorkSubmission — SubmissionAttachment | 1 : 0..M | ✅ | `SubmissionAttachment.submission_id` FK, `NOT NULL`; `storage_key UNIQUE` | Files stay outside MySQL; only metadata is stored. |
| R11 | WorkSubmission — WorkVerification | 1 : 0..1 | ⚠️ | `WorkVerification.submission_id` FK + `UNIQUE` | `approved_hours` must depend on the decision (I7). The proposal doesn't record *who* verified — see proposed R20 below. |
| R12 | Application — Feedback | 1 : 0..M | ⚠️ | `Feedback.application_id` FK, `NOT NULL` | Decide whether one author can leave more than one feedback per application (open decision 6). |
| R13 | UserAccount — Feedback | 1 : 0..M | ❌ | Split into two relationships: `Feedback.author_user_id` and `Feedback.recipient_user_id`, both FK → UserAccount | Listed as one relationship but it is two. Both users must be participants in the linked application (I2). |
| R14 | Feedback — AdminReview | 1 : 0..1 | ⚠️ | `AdminReview.feedback_id` FK + `UNIQUE` | Approval status is stored in both tables (I1). |
| R15 | UserAccount — AdminReview | 1 : 0..M | ⚠️ | `AdminReview.reviewer_user_id` FK, `NOT NULL` | Reviewer must have `role = Admin` (I6). |
| R16 | ContributorProfile — Badge (via ContributorBadge) | M : N | ⚠️ | Surrogate PK `contributor_badge_id` (PointTransaction references it) | Add `UNIQUE (contributor_id, badge_id)` if a badge can only be earned once (I9). |
| R17 | ContributorProfile — PointTransaction | 1 : 0..M | ⚠️ | `PointTransaction.contributor_id` FK, `NOT NULL` | Contributor is also reachable through the point's source — accepted redundancy (I3). |
| R18 | WorkVerification — PointTransaction | 1 : 0..1 | ⚠️ | `PointTransaction.verification_id` FK, nullable, `UNIQUE` | Exclusive with R19 (I5). Only *approved* verifications may award points (I7). |
| R19 | ContributorBadge — PointTransaction | 1 : 0..1 | ⚠️ | `PointTransaction.contributor_badge_id` FK, nullable, `UNIQUE` | Exclusive with R18 (I5). |

**Result:** 6 valid as proposed, 12 valid with an added constraint, 1 needs to change.

**Proposed new relationship**

| # | Relationship | Card. | Implementation | Why |
|---|---|---|---|---|
| R20 | UserAccount — WorkVerification | 1 : 0..M | `WorkVerification.verified_by_user_id` FK, `NOT NULL` | Records who actually verified the work. This is a historical fact, not redundant: an organization's manager can change later, so it can't be reliably derived. Supports the "only authorized Creators verify" rule and gives an audit trail. |

## 4. Issues and proposed fixes

### I1 — Feedback approval status is stored twice (R14)

The proposal gives Feedback an "approval status" and AdminReview an "approval or rejection". These are the same fact in two tables, so they can disagree (an update anomaly).

**Fix (recommended):** remove `approval_status` from Feedback and derive it:

- no AdminReview row → `pending`
- otherwise → `AdminReview.decision`

Expose it through a view (`v_feedback_status`) so queries stay simple.

**Alternative:** keep the column as a cache, but always update it in the same transaction that inserts the AdminReview.

### I2 — UserAccount—Feedback is two relationships, not one (R13)

Each Feedback row has an author and a recipient, so it needs two FKs to UserAccount, plus:

- `CHECK (author_user_id <> recipient_user_id)`
- a rule that both users are participants in the linked application — the Contributor who applied, and the Creator managing the opportunity's organization. A FK can't check this; it needs a `BEFORE INSERT` trigger or backend validation.

*Trade-off considered:* storing a `direction` column (`contributor_to_creator` / `creator_to_contributor`) and deriving both users from the application would remove the redundancy, but every rating and moderation query would need extra joins. Keeping the two FKs plus the participant check is simpler and safer for this project.

### I3 — Stored vs. calculated totals: ENSF 607 and ENSF 608 disagree

- **ENSF 607 design (README event table):** `WORK_VERIFIED` "updates verified hours and skills"; `FEEDBACK_APPROVED` "updates public ratings". This implies stored totals.
- **ENSF 608 proposal:** verified hours, average Creator rating and leaderboard totals are calculated from approved records.

Storing totals that can be calculated creates redundancy; if an event fails or is retried, the stored total drifts from the real records.

**Fix (recommended):** no stored totals. Create views:

- `v_contributor_verified_hours` — `SUM(approved_hours)` over approved verifications
- `v_creator_rating` — `AVG(rating)` over Admin-approved feedback only
- `v_leaderboard` — `SUM(amount)` from PointTransaction for a given period

The consumer services keep sending notifications, and read totals from these views. If performance later needs a cache, document it as deliberate denormalization and recompute it in the same transaction.

**Related accepted redundancy:** `PointTransaction.contributor_id` can be derived through the point's source (verification → submission → application → contributor, or badge → contributor). It is kept on purpose so leaderboard queries don't need four joins; the backend must set it consistently.

**Needs a team decision.**

### I4 — Is the rating for the Creator account or the organization? (R2, R13)

Feedback's recipient is a UserAccount, but one Creator can manage several organizations. The proposal says "public Creator ratings", which is ambiguous.

- **Option A — rate the Creator account:** works with the current design.
- **Option B — rate the organization:** the organization is derivable through application → opportunity → organization, so no extra column is needed.

**Recommendation:** Option B, since Contributors see the organization on each listing. **Needs a team decision.**

### I5 — PointTransaction has two possible sources (R17–R19)

Each point entry comes from either a verification or a badge — never both, never neither.

**Fix:**

```sql
verification_id       INT NULL UNIQUE,
contributor_badge_id  INT NULL UNIQUE,
CONSTRAINT chk_point_source CHECK (
  (verification_id IS NOT NULL) + (contributor_badge_id IS NOT NULL) = 1
)
```

- The `UNIQUE` keys enforce "points awarded only once per verification or badge". MySQL allows several `NULL`s in a `UNIQUE` index, so the rule only applies to filled values.
- MySQL enforces `CHECK` constraints from version 8.0.16.
- MySQL doesn't allow a `CHECK` on a column that has an `ON DELETE` / `ON UPDATE` referential action, so leave these two FKs with the default (`RESTRICT`) behaviour.

### I6 — Role rules that a foreign key can't enforce (R1, R2, R15)

A FK to UserAccount only checks that the user exists, not their role. And a MySQL `CHECK` can't look at another table. These rules need `BEFORE INSERT/UPDATE` triggers or validation in the FastAPI service layer:

- ContributorProfile only for `role = Contributor`
- CreatorOrganization manager only `role = Creator`
- AdminReview reviewer only `role = Admin`
- WorkVerification verifier (R20) only the Creator managing that opportunity's organization

**Also confirm:** a single `role` column means one account can't be both a Creator and a Contributor. This is fine for the MVP if intended.

### I7 — Workflow rules across tables (R8, R9, R11, R18)

| Rule | Where it's enforced |
|---|---|
| Apply only before the deadline and while under the applicant limit | Backend transaction that locks the Opportunity row (`SELECT … FOR UPDATE`) so two people can't take the last place at the same time |
| Submit work only for an `accepted` application | Trigger or backend check |
| `approved_hours` set only when the decision is approved | `CHECK ((decision = 'approved' AND approved_hours > 0) OR (decision = 'rejected' AND approved_hours IS NULL))` |
| Points only from `approved` verifications | Trigger or backend check |

**Open question:** does the applicant limit count all applications, or only accepted ones?

### I8 — Every 1 : 0..1 relationship needs a uniqueness guarantee (R1, R9, R11, R14)

Without it, the database would accept a second profile, submission, verification or review for the same parent.

| Relationship | Guarantee |
|---|---|
| R1 UserAccount — ContributorProfile | Shared PK |
| R9 Application — WorkSubmission | `UNIQUE (application_id)` |
| R11 WorkSubmission — WorkVerification | `UNIQUE (submission_id)` |
| R14 Feedback — AdminReview | `UNIQUE (feedback_id)` |

### I9 — Can a badge be earned more than once? (R16)

- **Once only:** add `UNIQUE (contributor_id, badge_id)`.
- **Repeatable:** leave it out; each earning gets its own row and its own point entry.

## 5. Open decisions for the team

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Stored vs. calculated totals (I3) | Stored totals updated by events / calculated views | Calculated views |
| 2 | Rating target (I4) | Creator account / organization | Organization |
| 3 | One role per account (I6) | Single role / multiple roles | Single role for MVP |
| 4 | Applicant limit (I7) | Counts all applications / accepted only | Team to decide |
| 5 | Badge repeatable? (I9) | Once only / repeatable | Once only |
| 6 | Feedback per application (R12) | One per author / many | One per author per application |

## 6. Next steps

- Formal 1NF → BCNF analysis after the Oct 16 normalization lecture, using `functional-dependencies.md`.
- Apply the agreed constraints in the shared schema DDL.
- Turn each rule in I5–I8 into a test case for database testing.
