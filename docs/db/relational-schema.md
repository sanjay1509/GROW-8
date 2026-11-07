# Relational Schema — Grow8 Database

**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty

> Generated Nov 7, 2026 from the loaded schema (`grow8-backend/db/init/001_schema.sql`) by `docs/diagrams/generate_er_diagram.py`: 18 relations, 124 attributes, 26 foreign keys. The same schema is drawn as an ER diagram in `docs/diagrams/GROW8-ER-Diagram.pdf` (page 1) and as this notation on page 2.

Notation: primary-key attributes are <ins>underlined</ins>, foreign-key attributes are *in italics*, and each foreign key is listed under its relation as `columns → relation(key)`. Types, nullability and meanings are in `data-dictionary.md`; functional dependencies and the BCNF check are in `functional-dependencies.md`.

## Identity and profiles

**user_account**(<ins>user_id</ins>, email, password_hash, role, full_name, is_active, created_at, updated_at)

- Candidate key `(email)`

**contributor_profile**(<ins>*user_id*</ins>, headline, bio, institution, city, created_at, updated_at)

- FK `user_id` → `user_account(user_id)`

**creator_organization**(<ins>organization_id</ins>, *owner_user_id*, name, organization_type, description, website, city, created_at, updated_at)

- FK `owner_user_id` → `user_account(user_id)`
- Candidate key `(owner_user_id)`

## Reference data

**opportunity_category**(<ins>category_id</ins>, code, name, description)

- Candidate key `(code)`
- Candidate key `(name)`

**skill**(<ins>skill_id</ins>, code, name)

- Candidate key `(code)`
- Candidate key `(name)`

**badge**(<ins>badge_id</ins>, code, name, description, points, required_verified_hours)

- Candidate key `(code)`
- Candidate key `(name)`

## Opportunities and skills

**opportunity**(<ins>opportunity_id</ins>, *organization_id*, *category_id*, title, description, requirements, location, work_mode, start_date, end_date, expected_hours, compensation_type, compensation_amount, compensation_details, applicant_limit, application_deadline, working_conditions, safety_information, accessibility_details, status, published_at, created_at, updated_at)

- FK `category_id` → `opportunity_category(category_id)`
- FK `organization_id` → `creator_organization(organization_id)`

**opportunity_skill**(<ins>*opportunity_id*</ins>, <ins>*skill_id*</ins>)

- FK `opportunity_id` → `opportunity(opportunity_id)`
- FK `skill_id` → `skill(skill_id)`

**contributor_skill**(<ins>*contributor_id*</ins>, <ins>*skill_id*</ins>, created_at)

- FK `contributor_id` → `contributor_profile(user_id)`
- FK `skill_id` → `skill(skill_id)`

## Applications and work

**application**(<ins>application_id</ins>, *opportunity_id*, *contributor_id*, status, motivation, submitted_at, decided_at)

- FK `contributor_id` → `contributor_profile(user_id)`
- FK `opportunity_id` → `opportunity(opportunity_id)`
- Candidate key `(opportunity_id, contributor_id)`

**work_submission**(<ins>submission_id</ins>, *application_id*, description, hours_claimed, submitted_at)

- FK `application_id` → `application(application_id)`
- Candidate key `(application_id)`

**submission_attachment**(<ins>attachment_id</ins>, *submission_id*, file_name, content_type, size_bytes, storage_key, uploaded_at)

- FK `submission_id` → `work_submission(submission_id)`
- Candidate key `(storage_key)`

## Verification and feedback

**work_verification**(<ins>verification_id</ins>, *submission_id*, *verified_by_user_id*, decision, verified_hours, comment, verified_at)

- FK `submission_id` → `work_submission(submission_id)`
- FK `verified_by_user_id` → `user_account(user_id)`
- Candidate key `(submission_id)`

**feedback**(<ins>feedback_id</ins>, *application_id*, *author_user_id*, *subject_user_id*, rating, comment, reports_discrepancy, created_at)

- FK `application_id` → `application(application_id)`
- FK `author_user_id` → `user_account(user_id)`
- FK `subject_user_id` → `user_account(user_id)`
- Candidate key `(application_id, author_user_id)`

**admin_review**(<ins>review_id</ins>, *feedback_id*, *admin_user_id*, decision, reason, reviewed_at)

- FK `admin_user_id` → `user_account(user_id)`
- FK `feedback_id` → `feedback(feedback_id)`
- Candidate key `(feedback_id)`

## Rewards

**contributor_badge**(<ins>*contributor_id*</ins>, <ins>*badge_id*</ins>, awarded_at)

- FK `badge_id` → `badge(badge_id)`
- FK `contributor_id` → `contributor_profile(user_id)`

**point_transaction**(<ins>transaction_id</ins>, *contributor_id*, points, source, *verification_id*, *badge_id*, created_at)

- FK `contributor_id` → `contributor_profile(user_id)`
- FK `contributor_id, badge_id` → `contributor_badge(contributor_id, badge_id)`
- FK `verification_id` → `work_verification(verification_id)`
- Candidate key `(contributor_id, badge_id)`
- Candidate key `(verification_id)`

## Notifications

**notification**(<ins>notification_id</ins>, *user_id*, event_id, notification_type, title, message, *opportunity_id*, read_at, created_at)

- FK `opportunity_id` → `opportunity(opportunity_id)`
- FK `user_id` → `user_account(user_id)`
- Candidate key `(user_id, event_id)`

## Views (derived, not stored)

- `v_contributor_skill`: verified once approved work used the skill
- `v_contributor_verified_hours`: SUM(verified_hours) of approved work_verification rows
- `v_feedback_status`: pending until an admin_review row exists
- `v_leaderboard`: SUM(points) from point_transaction, RANK() OVER
- `v_user_rating`: AVG(rating) of feedback approved in admin_review
