-- =============================================================================
-- GROW8 - ENSF 608: SQL answers to the eight database questions in the proposal.
--
-- Run against the dev database (001_schema + 002_seed + 004_seed_workflow):
--     make queries
-- or paste one block at a time into MySQL Workbench (localhost:3307).
--
-- Parameters are session variables so each query can be re-run with other
-- values. @as_of is fixed so the results match docs/db/database-questions.md;
-- in the application it would be NOW().
-- Each block starts with "-- Q<n>:" so the tests can run them one by one.
-- =============================================================================

SET @as_of       = '2026-11-07 12:00:00';
SET @category    = 'community';
SET @period_from = '2026-10-01 00:00:00';
SET @period_to   = '2026-11-01 00:00:00';

-- Q1: Which open opportunities match a category, and what are their deadlines,
--     hours, compensation, and safety rules?
-- "Open" means status = 'open' and the deadline has not passed yet.
-- Index used: ix_opportunity_category_status (category_id, status).
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

-- Q2: Which Contributors applied to each opportunity, and what are their
--     application statuses?
-- Also shows how many places are taken (pending + accepted) out of the limit.
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

-- Q3: Which accepted applications have work submissions awaiting Creator
--     verification?
-- Awaiting = a submission with no work_verification row yet.
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

-- Q4: How many verified experience hours has each Contributor accumulated from
--     approved work?
-- Same calculation as the v_contributor_verified_hours view; contributors with
-- no approved work show 0.
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

-- Q5: Which Contributors rank highest on the leaderboard by total points earned
--     in a given period?
-- Points are summed from the ledger inside [@period_from, @period_to); the
-- all-time ranking is the v_leaderboard view.
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

-- Q6: Which badges have been earned most often, and by how many Contributors?
-- Badges nobody has earned yet are listed with 0.
SELECT b.badge_id,
       b.name,
       b.points,
       COUNT(cb.contributor_id)  AS contributors_earned
FROM badge b
LEFT JOIN contributor_badge cb ON cb.badge_id = b.badge_id
GROUP BY b.badge_id, b.name, b.points
ORDER BY contributors_earned DESC, b.badge_id;

-- Q7: Which feedback entries reporting discrepancies are still awaiting Admin
--     review, and which opportunities were flagged?
-- Pending = no admin_review row (status is derived, never stored).
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

-- Q8: What is the average Creator rating based only on Admin-approved feedback?
-- Rejected and pending feedback never count. One organization per creator
-- (uq_creator_organization_owner), so this is also the organization's rating.
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
