# Database Questions — Grow8 Database

**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty

The ENSF 608 proposal lists eight questions the database must be able to answer. This document gives the SQL for each one and its result on the development data, so every answer can be checked by running it.

- **SQL file:** `grow8-backend/db/queries/database_questions.sql`. Run it with `make queries` (from `grow8-backend/`, with the stack up), or paste one block at a time into MySQL Workbench (`localhost:3307`).
- **Data:** `001_schema.sql` + `002_seed.sql` + `004_seed_workflow.sql`. The workflow seed adds 14 applications, 5 submissions, 4 verifications, 7 feedback entries, 5 admin reviews, 5 earned badges and 8 point transactions on top of the users and opportunities in 002.
- **Parameters:** session variables at the top of the file. `@as_of = '2026-11-07 12:00:00'` (the application would use `NOW()`), `@category = 'community'`, `@period_from` / `@period_to` = October 2026.
- **Tests:** `grow8-backend/api/tests/integration/test_db_workflow_seed.py` runs every query on the same data and checks the results below.

People in the data: admin Ada Admin (1); creators Priya Nair (2, Maple Street Bakery), Daniel Okafor (3, Bow River Community Food Bank), Sofia Martinez (4, YYC Neighbourhood Events); contributors Alex Chen (5), Jordan Lee (6), Sam Patel (7).

## Summary

| # | Question | Main tables | Answer on the dev data |
|---|---|---|---|
| Q1 | Open opportunities in a category | `opportunity`, `opportunity_category`, `creator_organization` | 5 open community opportunities, soonest deadline first |
| Q2 | Applicants and statuses per opportunity | `application`, `opportunity`, `user_account` | 14 applications; opportunities 1 and 2 are full |
| Q3 | Submissions awaiting verification | `work_submission`, `application`, `work_verification` | 1: Alex Chen's warehouse count, for Daniel Okafor |
| Q4 | Verified hours per contributor | `work_verification`, `work_submission`, `application` | Jordan 14.00, Alex 5.00, Sam 0.00 |
| Q5 | Leaderboard for a period | `point_transaction`, `user_account` | October: Jordan Lee, 105 points |
| Q6 | Most earned badges | `badge`, `contributor_badge` | First Verified Task and Community Helper (2 each) |
| Q7 | Discrepancy reports awaiting review | `feedback`, `admin_review`, `application`, `opportunity` | 1: Sam Patel on the warehouse count (opportunity 10) |
| Q8 | Average creator rating, approved feedback only | `feedback`, `admin_review`, `creator_organization` | Bow River Community Food Bank: 4.50 from 2 reviews |

## Queries and results

### Q1. Which open opportunities match a category, and what are their deadlines, hours, compensation, and safety rules?

Joins the category by its code and keeps only opportunities that are `open` with a deadline still ahead. Uses `ix_opportunity_category_status (category_id, status)`.

```sql
SELECT o.opportunity_id,
       o.title,
       org.name                  AS organization,
       o.application_deadline,
       o.expected_hours,
       o.compensation_type,
       o.compensation_amount,
       o.safety_information
FROM opportunity o
JOIN opportunity_category c ON c.category_id = o.category_id
JOIN creator_organization org ON org.organization_id = o.organization_id
WHERE c.code = @category
  AND o.status = 'open'
  AND o.application_deadline >= @as_of
ORDER BY o.application_deadline, o.opportunity_id;
```

**Result on the dev data** (5 rows):

| opportunity_id | title | organization | application_deadline | expected_hours | compensation_type | compensation_amount | safety_information |
|---|---|---|---|---|---|---|---|
| 12 | Event photographer for community fun run | YYC Neighbourhood Events | 2026-11-08 23:59:59 | 5.00 | stipend | 100.00 | Stay off the running course; marshals will guide you. |
| 5 | Weekend food hamper packing | Bow River Community Food Bank | 2026-11-30 23:59:59 | 24.00 | unpaid |  | Closed-toe shoes required; lifting training on the first shift. |
| 4 | Holiday market booth assistant | Maple Street Bakery | 2026-12-01 23:59:59 | 16.00 | paid | 320.00 | Food safety briefing on the first shift; gloves and aprons provided. |
| 8 | Winter lantern festival setup crew | YYC Neighbourhood Events | 2026-12-10 23:59:59 | 12.00 | paid | 264.00 | Winter clothing required; site safety briefing and high-visibility vests provided. |
| 13 | New Year's Eve family event greeters | YYC Neighbourhood Events | 2026-12-20 23:59:59 | 6.00 | unpaid |  | Crowd management briefing before the shift; staff security on site. |

### Q2. Which Contributors applied to each opportunity, and what are their application statuses?

One row per application. A window function counts the places taken (pending + accepted) next to the limit, the same rule `trg_application_bi` enforces. Uses `ix_application_opportunity_status`.

```sql
SELECT o.opportunity_id,
       o.title,
       ua.full_name              AS contributor,
       a.status,
       a.submitted_at,
       SUM(a.status IN ('pending', 'accepted')) OVER (PARTITION BY o.opportunity_id)
                                 AS places_taken,
       o.applicant_limit
FROM application a
JOIN opportunity o ON o.opportunity_id = a.opportunity_id
JOIN user_account ua ON ua.user_id = a.contributor_id
ORDER BY o.opportunity_id, a.submitted_at;
```

**Result on the dev data** (14 rows):

| opportunity_id | title | contributor | status | submitted_at | places_taken | applicant_limit |
|---|---|---|---|---|---|---|
| 1 | Digitize paper recipe archive | Jordan Lee | pending | 2026-11-02 18:00:00 | 2 | 2 |
| 1 | Digitize paper recipe archive | Sam Patel | pending | 2026-11-03 19:00:00 | 2 | 2 |
| 2 | Inventory spreadsheet cleanup | Jordan Lee | rejected | 2026-10-27 16:00:00 | 1 | 1 |
| 2 | Inventory spreadsheet cleanup | Alex Chen | accepted | 2026-10-28 17:00:00 | 1 | 1 |
| 3 | Social media content calendar for the holiday season | Sam Patel | pending | 2026-10-25 20:00:00 | 1 | 2 |
| 3 | Social media content calendar for the holiday season | Alex Chen | withdrawn | 2026-10-26 22:00:00 | 1 | 2 |
| 5 | Weekend food hamper packing | Jordan Lee | accepted | 2026-10-15 15:00:00 | 1 | 10 |
| 10 | Warehouse inventory count | Jordan Lee | accepted | 2026-10-02 17:00:00 | 3 | 6 |
| 10 | Warehouse inventory count | Sam Patel | accepted | 2026-10-03 19:00:00 | 3 | 6 |
| 10 | Warehouse inventory count | Alex Chen | accepted | 2026-10-04 21:00:00 | 3 | 6 |
| 11 | Summer BBQ volunteer crew | Jordan Lee | accepted | 2026-07-10 16:00:00 | 2 | 8 |
| 11 | Summer BBQ volunteer crew | Alex Chen | accepted | 2026-07-12 18:30:00 | 2 | 8 |
| 11 | Summer BBQ volunteer crew | Sam Patel | rejected | 2026-07-20 20:00:00 | 2 | 8 |
| 12 | Event photographer for community fun run | Sam Patel | accepted | 2026-10-20 18:00:00 | 1 | 2 |

### Q3. Which accepted applications have work submissions awaiting Creator verification?

A submission is awaiting verification when it has no `work_verification` row (anti-join with `LEFT JOIN … IS NULL`). The verifier shown is the organization's owner, the only person `trg_work_verification_bi` lets verify.

```sql
SELECT ws.submission_id,
       o.title                   AS opportunity,
       ua.full_name              AS contributor,
       ws.hours_claimed,
       ws.submitted_at,
       org.name                  AS organization,
       owner.full_name           AS verifier
FROM work_submission ws
JOIN application a ON a.application_id = ws.application_id AND a.status = 'accepted'
JOIN opportunity o ON o.opportunity_id = a.opportunity_id
JOIN creator_organization org ON org.organization_id = o.organization_id
JOIN user_account owner ON owner.user_id = org.owner_user_id
JOIN user_account ua ON ua.user_id = a.contributor_id
LEFT JOIN work_verification wv ON wv.submission_id = ws.submission_id
WHERE wv.verification_id IS NULL
ORDER BY ws.submitted_at;
```

**Result on the dev data** (1 row):

| submission_id | opportunity | contributor | hours_claimed | submitted_at | organization | verifier |
|---|---|---|---|---|---|---|
| 5 | Warehouse inventory count | Alex Chen | 8.00 | 2026-10-18 15:00:00 | Bow River Community Food Bank | Daniel Okafor |

### Q4. How many verified experience hours has each Contributor accumulated from approved work?

Sums `verified_hours` over approved verifications only; contributors without approved work still appear with 0 because the joins start from `contributor_profile`. Same logic as the `v_contributor_verified_hours` view.

```sql
SELECT cp.user_id                AS contributor_id,
       ua.full_name,
       COALESCE(SUM(wv.verified_hours), 0) AS verified_hours,
       COUNT(wv.verification_id) AS completed_opportunities
FROM contributor_profile cp
JOIN user_account ua ON ua.user_id = cp.user_id
LEFT JOIN application a ON a.contributor_id = cp.user_id
LEFT JOIN work_submission ws ON ws.application_id = a.application_id
LEFT JOIN work_verification wv
       ON wv.submission_id = ws.submission_id AND wv.decision = 'approved'
GROUP BY cp.user_id, ua.full_name
ORDER BY verified_hours DESC, cp.user_id;
```

**Result on the dev data** (3 rows):

| contributor_id | full_name | verified_hours | completed_opportunities |
|---|---|---|---|
| 6 | Jordan Lee | 14.00 | 2 |
| 5 | Alex Chen | 5.00 | 1 |
| 7 | Sam Patel | 0.00 | 0 |

### Q5. Which Contributors rank highest on the leaderboard by total points earned in a given period?

Sums the points ledger inside a date range and ranks with `RANK()`, so ties share a rank. The all-time version is the `v_leaderboard` view. The period here is October 2026.

```sql
SELECT ua.user_id                AS contributor_id,
       ua.full_name,
       SUM(pt.points)            AS period_points,
       RANK() OVER (ORDER BY SUM(pt.points) DESC) AS period_rank
FROM point_transaction pt
JOIN user_account ua ON ua.user_id = pt.contributor_id AND ua.is_active = TRUE
WHERE pt.created_at >= @period_from
  AND pt.created_at <  @period_to
GROUP BY ua.user_id, ua.full_name
ORDER BY period_rank, ua.user_id;
```

**Result on the dev data** (1 row):

| contributor_id | full_name | period_points | period_rank |
|---|---|---|---|
| 6 | Jordan Lee | 105 | 1 |

### Q6. Which badges have been earned most often, and by how many Contributors?

Counts earners per badge; the `LEFT JOIN` keeps badges nobody has earned yet.

```sql
SELECT b.badge_id,
       b.name,
       b.points,
       COUNT(cb.contributor_id)  AS contributors_earned
FROM badge b
LEFT JOIN contributor_badge cb ON cb.badge_id = b.badge_id
GROUP BY b.badge_id, b.name, b.points
ORDER BY contributors_earned DESC, b.badge_id;
```

**Result on the dev data** (4 rows):

| badge_id | name | points | contributors_earned |
|---|---|---|---|
| 1 | First Verified Task | 10 | 2 |
| 4 | Community Helper | 20 | 2 |
| 2 | 10 Verified Hours | 25 | 1 |
| 3 | 50 Verified Hours | 100 | 0 |

### Q7. Which feedback entries reporting discrepancies are still awaiting Admin review, and which opportunities were flagged?

Discrepancy reports are feedback with `reports_discrepancy = TRUE`; pending means no `admin_review` row yet (status is derived, never stored, I1). Feedback 7 also reports a discrepancy but was already reviewed, so it is not listed.

```sql
SELECT f.feedback_id,
       o.opportunity_id,
       o.title                   AS opportunity,
       author.full_name          AS reported_by,
       subject.full_name         AS about,
       f.rating,
       f.comment,
       f.created_at
FROM feedback f
JOIN application a ON a.application_id = f.application_id
JOIN opportunity o ON o.opportunity_id = a.opportunity_id
JOIN user_account author ON author.user_id = f.author_user_id
JOIN user_account subject ON subject.user_id = f.subject_user_id
LEFT JOIN admin_review ar ON ar.feedback_id = f.feedback_id
WHERE f.reports_discrepancy = TRUE
  AND ar.review_id IS NULL
ORDER BY f.created_at;
```

**Result on the dev data** (1 row):

| feedback_id | opportunity_id | opportunity | reported_by | about | rating | comment | created_at |
|---|---|---|---|---|---|---|---|
| 5 | 10 | Warehouse inventory count | Sam Patel | Daniel Okafor | 1 | I worked both days but my hours were rejected. The count sheets were handed in on paper. | 2026-10-20 15:00:00 |

### Q8. What is the average Creator rating based only on Admin-approved feedback?

Averages only feedback with an approved `admin_review`. Rejected (feedback 4) and pending (feedback 5, 6) feedback do not count. With one organization per creator this is also the organization's rating.

```sql
SELECT ua.user_id                AS creator_id,
       ua.full_name              AS creator,
       org.name                  AS organization,
       ROUND(AVG(f.rating), 2)   AS average_rating,
       COUNT(*)                  AS approved_feedback_count
FROM feedback f
JOIN admin_review ar ON ar.feedback_id = f.feedback_id AND ar.decision = 'approved'
JOIN user_account ua ON ua.user_id = f.subject_user_id AND ua.role = 'creator'
JOIN creator_organization org ON org.owner_user_id = ua.user_id
GROUP BY ua.user_id, ua.full_name, org.name
ORDER BY average_rating DESC, ua.user_id;
```

**Result on the dev data** (1 row):

| creator_id | creator | organization | average_rating | approved_feedback_count |
|---|---|---|---|---|
| 3 | Daniel Okafor | Bow River Community Food Bank | 4.50 | 2 |
