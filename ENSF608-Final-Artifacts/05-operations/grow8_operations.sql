-- =============================================================================
-- GROW8 - ENSF 608 Database Operations
--
-- Every operation, query and stored procedure for the Grow8 database, grouped by
-- category. Each block starts with an ID and a short description of its purpose:
--
--   PART 1  SP-1 .. SP-9    Stored procedures (definitions)
--   PART 2  Q-1  .. Q-15    Retrieval queries (Q-1..Q-8 answer the proposal's
--                           eight database questions)
--           V-1  .. V-5     Views that calculate derived values
--   PART 3  OP-1 .. OP-22   Data modification (INSERT / UPDATE / DELETE and
--                           stored procedure calls), following one workflow
--   PART 4  IC-1 .. IC-18   Integrity checks: statements that MUST fail; the
--                           error message is the evidence that the rule holds
--
-- Run after 04-implementation/run_all.sql, against the same database:
--     mysql -u root -p --force -t grow8_608 < grow8_operations.sql
-- --force keeps going after the expected errors in parts 3 and 4.
-- In MySQL Workbench: open the file, turn on Query > "Continue on SQL Script
-- Error" (otherwise Workbench stops at the first expected error), then run it.
--
-- Parts 3 and 4 run inside one transaction that is rolled back at the end, so
-- the loaded dataset is unchanged and the file can be run any number of times.
-- The stored procedures are defined first, outside the transaction (MySQL commits
-- DDL automatically), and stay in the database.
--
-- Evidence of a full run: Operations-Evidence.md (made by generate_evidence.py).
-- =============================================================================

USE grow8_608;


-- =============================================================================
-- PART 1 - STORED PROCEDURES
-- The integrity procedures grow8_require_* (10, called by the triggers) are part
-- of the schema in 01_create_schema.sql. The procedures below are the
-- application's operations; they rely on those triggers for the shared rules.
-- =============================================================================

DELIMITER $$

-- [SP-1] sp_publish_opportunity: a creator publishes one of their drafts.
--   Checks ownership and draft status; the CHECK chk_opportunity_published_complete
--   then refuses the update if a mandatory disclosure is missing.
DROP PROCEDURE IF EXISTS sp_publish_opportunity $$
CREATE PROCEDURE sp_publish_opportunity(
    IN p_opportunity_id INT UNSIGNED, IN p_creator_user_id INT UNSIGNED)
BEGIN
    DECLARE v_owner INT UNSIGNED;
    DECLARE v_status VARCHAR(20);
    SET v_owner = (SELECT org.owner_user_id
                     FROM opportunity o
                     JOIN creator_organization org ON org.organization_id = o.organization_id
                    WHERE o.opportunity_id = p_opportunity_id);
    SET v_status = (SELECT status FROM opportunity WHERE opportunity_id = p_opportunity_id);
    IF v_owner IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'not_found: no such opportunity';
    END IF;
    IF v_owner <> p_creator_user_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'not_owner: only the organization''s owner can publish it';
    END IF;
    IF v_status <> 'draft' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'not_draft: only a draft can be published';
    END IF;
    UPDATE opportunity
       SET status = 'open', published_at = NOW()
     WHERE opportunity_id = p_opportunity_id;
END $$

-- [SP-2] sp_apply_to_opportunity: a contributor applies, or re-applies after withdrawing.
--   A new application is an INSERT; the triggers check that the opportunity is open,
--   the deadline has not passed and a place is free. Re-applying reuses the
--   withdrawn row with a new submission time (ADR 0021). Returns the application id.
DROP PROCEDURE IF EXISTS sp_apply_to_opportunity $$
CREATE PROCEDURE sp_apply_to_opportunity(
    IN p_contributor_id INT UNSIGNED, IN p_opportunity_id INT UNSIGNED,
    IN p_motivation TEXT, OUT p_application_id INT UNSIGNED)
BEGIN
    DECLARE v_id INT UNSIGNED;
    DECLARE v_status VARCHAR(20);
    SET v_id = (SELECT application_id FROM application
                 WHERE contributor_id = p_contributor_id AND opportunity_id = p_opportunity_id);
    SET v_status = (SELECT status FROM application WHERE application_id = v_id);
    IF v_status = 'withdrawn' THEN
        IF (SELECT status <> 'open' OR application_deadline < NOW()
              FROM opportunity WHERE opportunity_id = p_opportunity_id) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'application_closed: opportunity is not open for applications';
        END IF;
        UPDATE application
           SET status = 'pending', motivation = p_motivation,
               submitted_at = NOW(), decided_at = NULL
         WHERE application_id = v_id;
        SET p_application_id = v_id;
    ELSE
        INSERT INTO application (opportunity_id, contributor_id, motivation)
        VALUES (p_opportunity_id, p_contributor_id, p_motivation);
        SET p_application_id = LAST_INSERT_ID();
    END IF;
END $$

-- [SP-3] sp_decide_application: the creator who owns the opportunity accepts or
--   rejects a pending application. A rejected application frees its place.
DROP PROCEDURE IF EXISTS sp_decide_application $$
CREATE PROCEDURE sp_decide_application(
    IN p_application_id INT UNSIGNED, IN p_creator_user_id INT UNSIGNED,
    IN p_decision VARCHAR(20))
BEGIN
    DECLARE v_owner INT UNSIGNED;
    DECLARE v_status VARCHAR(20);
    IF p_decision NOT IN ('accepted', 'rejected') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invalid_decision: use accepted or rejected';
    END IF;
    SET v_owner = (SELECT org.owner_user_id
                     FROM application a
                     JOIN opportunity o ON o.opportunity_id = a.opportunity_id
                     JOIN creator_organization org ON org.organization_id = o.organization_id
                    WHERE a.application_id = p_application_id);
    SET v_status = (SELECT status FROM application WHERE application_id = p_application_id);
    IF v_owner IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'not_found: no such application';
    END IF;
    IF v_owner <> p_creator_user_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'not_owner: only the organization''s owner can decide applications';
    END IF;
    IF v_status <> 'pending' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'not_pending: only a pending application can be decided';
    END IF;
    UPDATE application
       SET status = p_decision, decided_at = NOW()
     WHERE application_id = p_application_id;
END $$

-- [SP-4] sp_verify_work: the creator approves (with verified hours) or rejects a
--   work submission. Approval also writes the points to the ledger: 10 points per
--   verified hour. Triggers check the verifier owns the opportunity; the CHECK
--   allows hours only on an approval; the unique key allows one verification.
DROP PROCEDURE IF EXISTS sp_verify_work $$
CREATE PROCEDURE sp_verify_work(
    IN p_submission_id INT UNSIGNED, IN p_creator_user_id INT UNSIGNED,
    IN p_decision VARCHAR(20), IN p_hours DECIMAL(6, 2), IN p_comment TEXT,
    OUT p_verification_id INT UNSIGNED)
BEGIN
    DECLARE v_contributor INT UNSIGNED;
    INSERT INTO work_verification (submission_id, verified_by_user_id, decision, verified_hours, comment)
    VALUES (p_submission_id, p_creator_user_id, p_decision, p_hours, p_comment);
    SET p_verification_id = LAST_INSERT_ID();
    IF p_decision = 'approved' THEN
        SET v_contributor = (SELECT a.contributor_id
                               FROM work_submission ws
                               JOIN application a ON a.application_id = ws.application_id
                              WHERE ws.submission_id = p_submission_id);
        INSERT INTO point_transaction (contributor_id, points, source, verification_id)
        VALUES (v_contributor, ROUND(p_hours * 10), 'work_verified', p_verification_id);
    END IF;
END $$

-- [SP-5] sp_award_badge: awards a badge once its hour requirement is met, and adds
--   the badge's points to the ledger. The primary key of contributor_badge allows
--   each badge once per contributor.
DROP PROCEDURE IF EXISTS sp_award_badge $$
CREATE PROCEDURE sp_award_badge(IN p_contributor_id INT UNSIGNED, IN p_badge_id INT UNSIGNED)
BEGIN
    DECLARE v_points INT UNSIGNED;
    DECLARE v_required DECIMAL(6, 2);
    DECLARE v_hours DECIMAL(28, 2);
    SET v_points = (SELECT points FROM badge WHERE badge_id = p_badge_id);
    SET v_required = (SELECT required_verified_hours FROM badge WHERE badge_id = p_badge_id);
    SET v_hours = (SELECT verified_hours FROM v_contributor_verified_hours
                    WHERE contributor_id = p_contributor_id);
    IF v_points IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'not_found: no such badge';
    END IF;
    IF v_required IS NOT NULL AND COALESCE(v_hours, 0) < v_required THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'badge_requirement_not_met: not enough verified hours for this badge';
    END IF;
    INSERT INTO contributor_badge (contributor_id, badge_id) VALUES (p_contributor_id, p_badge_id);
    INSERT INTO point_transaction (contributor_id, points, source, badge_id)
    VALUES (p_contributor_id, v_points, 'badge_awarded', p_badge_id);
END $$

-- [SP-6] sp_review_feedback: an admin approves or rejects a feedback entry. Only
--   approved feedback counts toward ratings (v_user_rating). The trigger checks the
--   reviewer is an admin; the unique key allows one review per feedback.
DROP PROCEDURE IF EXISTS sp_review_feedback $$
CREATE PROCEDURE sp_review_feedback(
    IN p_feedback_id INT UNSIGNED, IN p_admin_user_id INT UNSIGNED,
    IN p_decision VARCHAR(20), IN p_reason VARCHAR(500))
BEGIN
    INSERT INTO admin_review (feedback_id, admin_user_id, decision, reason)
    VALUES (p_feedback_id, p_admin_user_id, p_decision, p_reason);
END $$

-- [SP-7] sp_review_report: an admin dismisses a report, or upholds it. Upholding
--   upholds every other pending report on the same opportunity and takes the
--   opportunity down (status cancelled). A takedown must give a reason (CHECK).
DROP PROCEDURE IF EXISTS sp_review_report $$
CREATE PROCEDURE sp_review_report(
    IN p_report_id INT UNSIGNED, IN p_admin_user_id INT UNSIGNED,
    IN p_decision VARCHAR(20), IN p_reason VARCHAR(500))
BEGIN
    DECLARE v_opportunity INT UNSIGNED;
    SET v_opportunity = (SELECT opportunity_id FROM opportunity_report WHERE report_id = p_report_id);
    IF v_opportunity IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'not_found: no such report';
    END IF;
    INSERT INTO report_review (report_id, admin_user_id, decision, reason)
    VALUES (p_report_id, p_admin_user_id, p_decision, p_reason);
    IF p_decision = 'upheld' THEN
        INSERT INTO report_review (report_id, admin_user_id, decision, reason)
        SELECT r.report_id, p_admin_user_id, 'upheld', p_reason
          FROM opportunity_report r
          LEFT JOIN report_review rr ON rr.report_id = r.report_id
         WHERE r.opportunity_id = v_opportunity AND rr.review_id IS NULL;
        UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = v_opportunity;
    END IF;
END $$

-- [SP-8] sp_contributor_summary: a contributor's dashboard in two result sets:
--   totals (hours, completed work, points, rank, rating) and their skills, listed
--   or earned through approved work. Everything comes from the views.
DROP PROCEDURE IF EXISTS sp_contributor_summary $$
CREATE PROCEDURE sp_contributor_summary(IN p_contributor_id INT UNSIGNED)
BEGIN
    SELECT ua.user_id, ua.full_name,
           h.verified_hours, h.completed_opportunities,
           COALESCE(l.total_points, 0) AS total_points, l.leaderboard_rank,
           r.average_rating, COALESCE(r.approved_feedback_count, 0) AS approved_ratings
      FROM user_account ua
      JOIN v_contributor_verified_hours h ON h.contributor_id = ua.user_id
      LEFT JOIN v_leaderboard l ON l.contributor_id = ua.user_id
      LEFT JOIN v_user_rating r ON r.user_id = ua.user_id
     WHERE ua.user_id = p_contributor_id;
    SELECT s.name AS skill, cs.is_listed, cs.is_verified, cs.verified_at
      FROM v_contributor_skill cs
      JOIN skill s ON s.skill_id = cs.skill_id
     WHERE cs.contributor_id = p_contributor_id
     ORDER BY cs.is_verified DESC, s.name;
END $$

-- [SP-9] sp_find_open_opportunities: search open opportunities still taking
--   applications, by category code and optionally by required skill code (NULL =
--   any), with the places left under the applicant limit.
DROP PROCEDURE IF EXISTS sp_find_open_opportunities $$
CREATE PROCEDURE sp_find_open_opportunities(
    IN p_category_code VARCHAR(50), IN p_skill_code VARCHAR(50))
BEGIN
    SELECT o.opportunity_id, o.title, org.name AS organization, c.name AS category,
           o.application_deadline, o.compensation_type, o.compensation_amount,
           o.applicant_limit - (SELECT COUNT(*) FROM application a
                                 WHERE a.opportunity_id = o.opportunity_id
                                   AND a.status IN ('pending', 'accepted')) AS places_left
      FROM opportunity o
      JOIN opportunity_category c ON c.category_id = o.category_id
      JOIN creator_organization org ON org.organization_id = o.organization_id
     WHERE o.status = 'open'
       AND o.application_deadline >= NOW()
       AND (p_category_code IS NULL OR c.code = p_category_code)
       AND (p_skill_code IS NULL OR EXISTS (
                SELECT 1 FROM opportunity_skill os JOIN skill s ON s.skill_id = os.skill_id
                 WHERE os.opportunity_id = o.opportunity_id AND s.code = p_skill_code))
     ORDER BY o.application_deadline, o.opportunity_id;
END $$

DELIMITER ;


-- =============================================================================
-- PART 2 - RETRIEVAL QUERIES AND VIEWS (read-only, on the loaded dataset)
-- Q-1 .. Q-8 use a fixed @as_of date so their answers match
-- docs/db/database-questions.md; in the application @as_of would be NOW().
-- =============================================================================

SET @as_of       = '2026-11-07 12:00:00';
SET @category    = 'community';
SET @period_from = '2026-10-01 00:00:00';
SET @period_to   = '2026-11-01 00:00:00';

-- [Q-1] Proposal question 1: which open opportunities match a category, and what
--   are their deadlines, hours, compensation and safety rules?
SELECT o.opportunity_id, o.title, org.name AS organization, o.application_deadline,
       o.expected_hours, o.compensation_type, o.compensation_amount, o.safety_information
FROM opportunity o
JOIN opportunity_category c ON c.category_id = o.category_id
JOIN creator_organization org ON org.organization_id = o.organization_id
WHERE c.code = @category
  AND o.status = 'open'
  AND o.application_deadline >= @as_of
ORDER BY o.application_deadline, o.opportunity_id;

-- [Q-2] Proposal question 2: which contributors applied to each opportunity, and
--   what are their application statuses? Also the places taken out of the limit.
SELECT o.opportunity_id, o.title, ua.full_name AS contributor, a.status, a.submitted_at,
       SUM(a.status IN ('pending', 'accepted')) OVER (PARTITION BY o.opportunity_id) AS places_taken,
       o.applicant_limit
FROM application a
JOIN opportunity o ON o.opportunity_id = a.opportunity_id
JOIN user_account ua ON ua.user_id = a.contributor_id
ORDER BY o.opportunity_id, a.submitted_at;

-- [Q-3] Proposal question 3: which accepted applications have work submissions
--   awaiting creator verification (a submission with no verification yet)?
SELECT ws.submission_id, o.title AS opportunity, ua.full_name AS contributor,
       ws.hours_claimed, ws.submitted_at, org.name AS organization, owner.full_name AS verifier
FROM work_submission ws
JOIN application a ON a.application_id = ws.application_id AND a.status = 'accepted'
JOIN opportunity o ON o.opportunity_id = a.opportunity_id
JOIN creator_organization org ON org.organization_id = o.organization_id
JOIN user_account owner ON owner.user_id = org.owner_user_id
JOIN user_account ua ON ua.user_id = a.contributor_id
LEFT JOIN work_verification wv ON wv.submission_id = ws.submission_id
WHERE wv.verification_id IS NULL
ORDER BY ws.submitted_at;

-- [Q-4] Proposal question 4: how many verified experience hours has each
--   contributor accumulated from approved work? (0 when none yet)
SELECT cp.user_id AS contributor_id, ua.full_name,
       COALESCE(SUM(wv.verified_hours), 0) AS verified_hours,
       COUNT(wv.verification_id) AS completed_opportunities
FROM contributor_profile cp
JOIN user_account ua ON ua.user_id = cp.user_id
LEFT JOIN application a ON a.contributor_id = cp.user_id
LEFT JOIN work_submission ws ON ws.application_id = a.application_id
LEFT JOIN work_verification wv ON wv.submission_id = ws.submission_id AND wv.decision = 'approved'
GROUP BY cp.user_id, ua.full_name
ORDER BY verified_hours DESC, cp.user_id;

-- [Q-5] Proposal question 5: which contributors rank highest on the leaderboard by
--   points earned in a given period? (all-time ranking: view v_leaderboard)
SELECT ua.user_id AS contributor_id, ua.full_name, SUM(pt.points) AS period_points,
       RANK() OVER (ORDER BY SUM(pt.points) DESC) AS period_rank
FROM point_transaction pt
JOIN user_account ua ON ua.user_id = pt.contributor_id AND ua.is_active = TRUE
WHERE pt.created_at >= @period_from AND pt.created_at < @period_to
GROUP BY ua.user_id, ua.full_name
ORDER BY period_rank, ua.user_id;

-- [Q-6] Proposal question 6: which badges have been earned most often, and by how
--   many contributors? Badges nobody has earned are listed with 0.
SELECT b.badge_id, b.name, b.points, COUNT(cb.contributor_id) AS contributors_earned
FROM badge b
LEFT JOIN contributor_badge cb ON cb.badge_id = b.badge_id
GROUP BY b.badge_id, b.name, b.points
ORDER BY contributors_earned DESC, b.badge_id;

-- [Q-7] Proposal question 7: which feedback entries reporting a discrepancy still
--   await admin review, and which opportunities were flagged?
SELECT f.feedback_id, o.opportunity_id, o.title AS opportunity, author.full_name AS reported_by,
       subject.full_name AS about, f.rating, f.comment, f.created_at
FROM feedback f
JOIN application a ON a.application_id = f.application_id
JOIN opportunity o ON o.opportunity_id = a.opportunity_id
JOIN user_account author ON author.user_id = f.author_user_id
JOIN user_account subject ON subject.user_id = f.subject_user_id
LEFT JOIN admin_review ar ON ar.feedback_id = f.feedback_id
WHERE f.reports_discrepancy = TRUE AND ar.review_id IS NULL
ORDER BY f.created_at;

-- [Q-8] Proposal question 8: what is the average creator rating based only on
--   admin-approved feedback?
SELECT ua.user_id AS creator_id, ua.full_name AS creator, org.name AS organization,
       ROUND(AVG(f.rating), 2) AS average_rating, COUNT(*) AS approved_feedback_count
FROM feedback f
JOIN admin_review ar ON ar.feedback_id = f.feedback_id AND ar.decision = 'approved'
JOIN user_account ua ON ua.user_id = f.subject_user_id AND ua.role = 'creator'
JOIN creator_organization org ON org.owner_user_id = ua.user_id
GROUP BY ua.user_id, ua.full_name, org.name
ORDER BY average_rating DESC, ua.user_id;

-- [Q-9] Contributor dashboard for every contributor: verified hours, points, rank
--   and public rating, combining three views.
SELECT ua.user_id, ua.full_name, h.verified_hours, h.completed_opportunities,
       l.total_points, l.leaderboard_rank, r.average_rating
FROM contributor_profile cp
JOIN user_account ua ON ua.user_id = cp.user_id
JOIN v_contributor_verified_hours h ON h.contributor_id = cp.user_id
LEFT JOIN v_leaderboard l ON l.contributor_id = cp.user_id
LEFT JOIN v_user_rating r ON r.user_id = cp.user_id
ORDER BY l.leaderboard_rank, ua.user_id;

-- [Q-10] Verified skills: which skills has approved work proved for each
--   contributor, including skills they never listed?
SELECT ua.full_name AS contributor, s.name AS skill, cs.is_listed, cs.verified_at
FROM v_contributor_skill cs
JOIN user_account ua ON ua.user_id = cs.contributor_id
JOIN skill s ON s.skill_id = cs.skill_id
WHERE cs.is_verified
ORDER BY ua.full_name, s.name;

-- [Q-11] Admin moderation queue: feedback still pending review, discrepancy
--   reports first.
SELECT fs.feedback_id, o.title AS opportunity, author.full_name AS author,
       subject.full_name AS subject, fs.rating, fs.reports_discrepancy
FROM v_feedback_status fs
JOIN application a ON a.application_id = fs.application_id
JOIN opportunity o ON o.opportunity_id = a.opportunity_id
JOIN user_account author ON author.user_id = fs.author_user_id
JOIN user_account subject ON subject.user_id = fs.subject_user_id
WHERE fs.status = 'pending'
ORDER BY fs.reports_discrepancy DESC, fs.feedback_id;

-- [Q-12] Opportunity reports by status: each report with its derived status
--   (pending until an admin reviews it) and the admin's decision.
SELECT r.report_id, o.title AS opportunity, reporter.full_name AS reported_by, r.reason,
       COALESCE(rr.decision, 'pending') AS status, rr.reason AS admin_reason
FROM opportunity_report r
JOIN opportunity o ON o.opportunity_id = r.opportunity_id
JOIN user_account reporter ON reporter.user_id = r.reporter_user_id
LEFT JOIN report_review rr ON rr.report_id = r.report_id
ORDER BY r.report_id;

-- [Q-13] Notification inbox for one user (Jordan Lee, user 6): unread first, then
--   newest first, with the unread count calculated, not stored.
SET @user_id = 6;
SELECT n.notification_id, n.notification_type, n.title,
       (n.read_at IS NULL) AS unread, n.created_at
FROM notification n
WHERE n.user_id = @user_id
ORDER BY (n.read_at IS NULL) DESC, n.created_at DESC;
SELECT COUNT(*) AS unread_count FROM notification WHERE user_id = @user_id AND read_at IS NULL;

-- [Q-14] Impact per organization: contributors whose work was verified, verified
--   hours delivered and approved submissions (SDG 8 reporting).
SELECT org.name AS organization,
       COUNT(DISTINCT a.contributor_id) AS contributors,
       SUM(wv.verified_hours) AS verified_hours,
       COUNT(*) AS approved_submissions
FROM work_verification wv
JOIN work_submission ws ON ws.submission_id = wv.submission_id
JOIN application a ON a.application_id = ws.application_id
JOIN opportunity o ON o.opportunity_id = a.opportunity_id
JOIN creator_organization org ON org.organization_id = o.organization_id
WHERE wv.decision = 'approved'
GROUP BY org.organization_id, org.name
ORDER BY verified_hours DESC;

-- [Q-15] Skill demand and supply: for each skill, how many open opportunities
--   require it and how many contributors list it.
SELECT s.name AS skill,
       (SELECT COUNT(*) FROM opportunity_skill os
          JOIN opportunity o ON o.opportunity_id = os.opportunity_id
         WHERE os.skill_id = s.skill_id AND o.status = 'open') AS open_opportunities_requiring,
       (SELECT COUNT(*) FROM contributor_skill cs WHERE cs.skill_id = s.skill_id) AS contributors_listing
FROM skill s
ORDER BY open_opportunities_requiring DESC, s.name;

-- [V-1] v_contributor_verified_hours: verified hours and completed opportunities
--   per contributor, from approved verifications only (never stored).
SELECT * FROM v_contributor_verified_hours ORDER BY contributor_id;

-- [V-2] v_leaderboard: all-time points and rank per active contributor, summed
--   from the point_transaction ledger.
SELECT * FROM v_leaderboard ORDER BY leaderboard_rank, contributor_id;

-- [V-3] v_user_rating: average rating per user from admin-approved feedback only.
SELECT * FROM v_user_rating ORDER BY user_id;

-- [V-4] v_feedback_status: each feedback's status, derived from its admin review
--   (pending when there is none).
SELECT * FROM v_feedback_status ORDER BY feedback_id;

-- [V-5] v_contributor_skill: listed and earned skills per contributor, with when
--   approved work first verified each one.
SELECT * FROM v_contributor_skill ORDER BY contributor_id, skill_id;

-- [SP-9 run] Open community opportunities that need customer service, and all
--   open knowledge-based ones (results depend on today's date).
CALL sp_find_open_opportunities('community', 'customer-service');
CALL sp_find_open_opportunities('knowledge', NULL);

-- [SP-8 run] Jordan Lee's dashboard before the workflow in part 3.
CALL sp_contributor_summary(6);


-- =============================================================================
-- PART 3 - DATA MODIFICATION OPERATIONS
-- One workflow, run inside a transaction that is rolled back at the end of
-- part 4. Users: 1 Ada (admin); creators 2 Priya (Maple Street Bakery),
-- 3 Daniel (food bank), 4 Sofia (YYC events); contributors 5 Alex, 6 Jordan,
-- 7 Sam, and Riley, who signs up in OP-1. Steps marked "expected error" are
-- refused on purpose.
-- =============================================================================

START TRANSACTION;

-- [OP-1] INSERT: a new contributor signs up: account, profile and listed skills.
--   (The password hash is the development one used by the seed accounts.)
INSERT INTO user_account (email, password_hash, role, full_name)
VALUES ('riley.brooks@grow8.dev', '$2b$12$a8YZn.bGHfAHW8/Cnlx79O0xINuQd4A/E33BxLnujHoSNljsRTacW',
        'contributor', 'Riley Brooks');
SET @riley = LAST_INSERT_ID();
INSERT INTO contributor_profile (user_id, headline, institution, city)
VALUES (@riley, 'First-year business student', 'University of Calgary', 'Calgary');
INSERT INTO contributor_skill (contributor_id, skill_id) VALUES (@riley, 7), (@riley, 8);
SELECT ua.user_id, ua.full_name, ua.role, cp.institution, COUNT(cs.skill_id) AS listed_skills
FROM user_account ua
JOIN contributor_profile cp ON cp.user_id = ua.user_id
LEFT JOIN contributor_skill cs ON cs.contributor_id = ua.user_id
WHERE ua.user_id = @riley
GROUP BY ua.user_id, ua.full_name, ua.role, cp.institution;

-- [OP-2] INSERT: Priya creates a draft opportunity (deadline 30 days from today,
--   two places) and lists the skills it requires.
INSERT INTO opportunity (
    organization_id, category_id, title, description, requirements, location, work_mode,
    start_date, end_date, expected_hours, compensation_type, compensation_amount,
    compensation_details, applicant_limit, application_deadline, working_conditions,
    safety_information, accessibility_details)
VALUES (
    1, 1, 'Holiday order spreadsheet setup',
    'Set up a spreadsheet to track holiday pre-orders and pickups.',
    'Comfortable with spreadsheets.', 'Calgary (Kensington)', 'hybrid',
    CURDATE() + INTERVAL 35 DAY, CURDATE() + INTERVAL 42 DAY, 10.00, 'paid', 200.00,
    'Paid on completion.', 2, NOW() + INTERVAL 30 DAY,
    'Mostly remote; one visit to the bakery.', 'No physical work involved.',
    'Visit can be replaced by a video call.');
SET @opp = LAST_INSERT_ID();
INSERT INTO opportunity_skill (opportunity_id, skill_id) VALUES (@opp, 2), (@opp, 3);
SELECT opportunity_id, title, status, applicant_limit, published_at
FROM opportunity WHERE opportunity_id = @opp;

-- [OP-3] UPDATE (via SP-1): Priya publishes the draft; it is now open.
CALL sp_publish_opportunity(@opp, 2);
SELECT opportunity_id, status, published_at IS NOT NULL AS published
FROM opportunity WHERE opportunity_id = @opp;

-- [OP-4] INSERT (via SP-2): Alex applies. One of two places is taken.
CALL sp_apply_to_opportunity(5, @opp, 'I build spreadsheets for my student club.', @alex_app);
SELECT @alex_app AS alex_application_id;

-- [OP-5] INSERT (via SP-2): Jordan applies. Both places are taken.
CALL sp_apply_to_opportunity(6, @opp, 'Organized and detail-oriented.', @jordan_app);
SELECT a.application_id, ua.full_name, a.status
FROM application a JOIN user_account ua ON ua.user_id = a.contributor_id
WHERE a.opportunity_id = @opp ORDER BY a.application_id;

-- [OP-6] Expected error: Sam applies while both places are taken
--   (trigger trg_application_bi: applicant_limit_reached).
CALL sp_apply_to_opportunity(7, @opp, 'Happy to help.', @sam_app);

-- [OP-7] UPDATE: Jordan withdraws, which frees a place.
UPDATE application SET status = 'withdrawn' WHERE application_id = @jordan_app;
SELECT COUNT(*) AS places_taken FROM application
WHERE opportunity_id = @opp AND status IN ('pending', 'accepted');

-- [OP-8] INSERT (via SP-2): Sam applies again and now gets the free place.
CALL sp_apply_to_opportunity(7, @opp, 'Happy to help.', @sam_app);
SELECT @sam_app AS sam_application_id;

-- [OP-9] UPDATE (via SP-3): Priya accepts Alex and rejects Sam; the rejection
--   frees Sam's place.
CALL sp_decide_application(@alex_app, 2, 'accepted');
CALL sp_decide_application(@sam_app, 2, 'rejected');
SELECT a.application_id, ua.full_name, a.status, a.decided_at IS NOT NULL AS decided
FROM application a JOIN user_account ua ON ua.user_id = a.contributor_id
WHERE a.opportunity_id = @opp ORDER BY a.application_id;

-- [OP-10] UPDATE (via SP-2): Jordan re-applies. The withdrawn row is reused with a
--   new submission time (same application_id), and takes the free place.
CALL sp_apply_to_opportunity(6, @opp, 'Still interested if a place is free.', @jordan_again);
SELECT @jordan_app AS first_application_id, @jordan_again AS reapplication_id,
       (SELECT status FROM application WHERE application_id = @jordan_again) AS status;

-- [OP-11] INSERT: Sam, accepted for the fun-run photographer role (application 8),
--   submits his work with one attached file.
INSERT INTO work_submission (application_id, description, hours_claimed)
VALUES (8, 'Photographed the start, the finish and the awards; 140 edited photos delivered.', 5.00);
SET @sub = LAST_INSERT_ID();
INSERT INTO submission_attachment (submission_id, file_name, content_type, size_bytes, storage_key)
VALUES (@sub, 'fun-run-photos.zip', 'application/zip', 52428800, CONCAT('dev/submissions/', @sub, '/fun-run-photos.zip'));
SELECT ws.submission_id, ws.hours_claimed, COUNT(sa.attachment_id) AS attachments
FROM work_submission ws LEFT JOIN submission_attachment sa ON sa.submission_id = ws.submission_id
WHERE ws.submission_id = @sub GROUP BY ws.submission_id, ws.hours_claimed;

-- [OP-12] Before verification: Sam's verified hours and points (views).
SELECT h.verified_hours, h.completed_opportunities, l.total_points
FROM v_contributor_verified_hours h JOIN v_leaderboard l ON l.contributor_id = h.contributor_id
WHERE h.contributor_id = 7;

-- [OP-13] INSERT (via SP-4): Sofia approves 5 hours. Points are written to the
--   ledger (50), and the views now count the hours and the photography skill.
CALL sp_verify_work(@sub, 4, 'approved', 5.00, 'Great photos, delivered on time.', @ver);
SELECT h.verified_hours, h.completed_opportunities, l.total_points
FROM v_contributor_verified_hours h JOIN v_leaderboard l ON l.contributor_id = h.contributor_id
WHERE h.contributor_id = 7;
SELECT s.name AS skill, cs.is_listed, cs.is_verified
FROM v_contributor_skill cs JOIN skill s ON s.skill_id = cs.skill_id
WHERE cs.contributor_id = 7 AND cs.is_verified;

-- [OP-14] INSERT (via SP-5): Sam earns "First Verified Task"; its 10 points are
--   added to the ledger.
CALL sp_award_badge(7, 1);
SELECT source, points, verification_id, badge_id FROM point_transaction
WHERE contributor_id = 7 ORDER BY transaction_id;

-- [OP-15] INSERT: Sam and Sofia leave feedback for each other on application 8.
INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating, comment)
VALUES (8, 7, 4, 5, 'Clear brief and friendly marshals.');
SET @fb_sam = LAST_INSERT_ID();
INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating, comment)
VALUES (8, 4, 7, 5, 'Excellent photos, on time.');
SET @fb_sofia = LAST_INSERT_ID();
SELECT feedback_id, rating, status FROM v_feedback_status WHERE application_id = 8;

-- [OP-16] INSERT (via SP-6): Ada approves both entries; Sofia now has a public
--   rating (v_user_rating).
CALL sp_review_feedback(@fb_sam, 1, 'approved', NULL);
CALL sp_review_feedback(@fb_sofia, 1, 'approved', NULL);
SELECT user_id, average_rating, approved_feedback_count FROM v_user_rating WHERE user_id IN (4, 7);

-- [OP-17] INSERT: Sam reports the Holiday market booth role, which already has
--   Jordan's pending report.
INSERT INTO opportunity_report (opportunity_id, reporter_user_id, reason, details)
VALUES (4, 7, 'misleading_terms', 'The pay works out lower than $20/h for the shifts described.');
SELECT r.report_id, reporter.full_name, COALESCE(rr.decision, 'pending') AS status
FROM opportunity_report r
JOIN user_account reporter ON reporter.user_id = r.reporter_user_id
LEFT JOIN report_review rr ON rr.report_id = r.report_id
WHERE r.opportunity_id = 4;

-- [OP-18] INSERT + UPDATE (via SP-7): Ada upholds Jordan's report. Both pending
--   reports are upheld and the opportunity is taken down (cancelled).
CALL sp_review_report(2, 1, 'upheld', 'The listed hours and pay do not match the shifts.');
SELECT r.report_id, rr.decision FROM opportunity_report r
JOIN report_review rr ON rr.report_id = r.report_id WHERE r.opportunity_id = 4;
SELECT opportunity_id, status FROM opportunity WHERE opportunity_id = 4;

-- [OP-19] UPDATE: Jordan reads his notifications; the unread count drops to 0.
SELECT COUNT(*) AS unread_before FROM notification WHERE user_id = 6 AND read_at IS NULL;
UPDATE notification SET read_at = NOW() WHERE user_id = 6 AND read_at IS NULL;
SELECT COUNT(*) AS unread_after FROM notification WHERE user_id = 6 AND read_at IS NULL;

-- [OP-20] DELETE: Sofia deletes her draft (opportunity 15). Its required skills
--   are deleted with it (ON DELETE CASCADE).
SELECT COUNT(*) AS skill_rows_before FROM opportunity_skill WHERE opportunity_id = 15;
DELETE FROM opportunity WHERE opportunity_id = 15 AND status = 'draft';
SELECT COUNT(*) AS opportunity_left FROM opportunity WHERE opportunity_id = 15;
SELECT COUNT(*) AS skill_rows_after FROM opportunity_skill WHERE opportunity_id = 15;

-- [OP-21] DELETE: Jordan removes "Customer service" from his listed skills.
--   Approved work proved it, so it stays as an earned, verified skill.
DELETE FROM contributor_skill WHERE contributor_id = 6 AND skill_id = 7;
SELECT s.name AS skill, cs.is_listed, cs.is_verified
FROM v_contributor_skill cs JOIN skill s ON s.skill_id = cs.skill_id
WHERE cs.contributor_id = 6 AND cs.skill_id = 7;


-- =============================================================================
-- PART 4 - INTEGRITY CHECKS (each statement must FAIL)
-- Still inside the transaction. The error message names the rule that refused
-- the change. None of these depends on today's date.
-- =============================================================================

-- [IC-1] PRIMARY KEY: a second skill with id 1.
INSERT INTO skill (skill_id, code, name) VALUES (1, 'duplicate', 'Duplicate skill');

-- [IC-2] FOREIGN KEY: an application for an opportunity that does not exist.
INSERT INTO application (opportunity_id, contributor_id) VALUES (999, 5);

-- [IC-3] UNIQUE (uq_feedback_application_author): Jordan leaves a second feedback
--   on the same application (he already rated the food bank for application 1).
INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating)
VALUES (1, 6, 3, 4);

-- [IC-4] CHECK (chk_feedback_rating): a rating outside 1-5.
INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating)
VALUES (4, 3, 6, 6);

-- [IC-5] CHECK (chk_opportunity_published_complete): publishing a draft with
--   missing disclosures (opportunity 14 has no dates, deadline or safety info).
CALL sp_publish_opportunity(14, 2);

-- [IC-6] CHECK (chk_work_verification_hours): a rejection that still claims hours.
INSERT INTO work_verification (submission_id, verified_by_user_id, decision, verified_hours)
VALUES (5, 3, 'rejected', 4.00);

-- [IC-7] TRIGGER (contributor_profile_role): a contributor profile for a creator.
INSERT INTO contributor_profile (user_id, headline) VALUES (2, 'Not a contributor');

-- [IC-8] TRIGGER (application_closed): Riley applies to a closed opportunity
--   (opportunity 11).
INSERT INTO application (opportunity_id, contributor_id) VALUES (11, @riley);

-- [IC-9] TRIGGER (application_deadline_passed): Riley applies to an opportunity
--   that is still open but whose deadline passed on 2026-10-10 (opportunity 10).
INSERT INTO application (opportunity_id, contributor_id) VALUES (10, @riley);

-- [IC-10] TRIGGER (submission_requires_accepted): work for an application that is
--   still pending (application 9).
INSERT INTO work_submission (application_id, description, hours_claimed)
VALUES (9, 'Drafted the calendar.', 3.00);

-- [IC-11] TRIGGER (verifier_not_owner): Priya verifies work done for the food bank.
INSERT INTO work_verification (submission_id, verified_by_user_id, decision, verified_hours)
VALUES (5, 2, 'approved', 8.00);

-- [IC-12] TRIGGER (feedback_participants): Alex leaves feedback on an application
--   he is not part of.
INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating)
VALUES (1, 5, 3, 4);

-- [IC-13] TRIGGER (points_require_approval): points for a rejected verification.
INSERT INTO point_transaction (contributor_id, points, source, verification_id)
VALUES (7, 80, 'work_verified', 4);

-- [IC-14] COMPOSITE FOREIGN KEY (fk_point_transaction_contributor_badge): badge
--   points for a badge the contributor never earned.
INSERT INTO point_transaction (contributor_id, points, source, badge_id)
VALUES (7, 100, 'badge_awarded', 3);

-- [IC-15] TRIGGER (role_locked): changing the role of an account that already has
--   contributor rows.
UPDATE user_account SET role = 'creator' WHERE user_id = 5;

-- [IC-16] TRIGGER (report_requires_published): reporting a draft.
INSERT INTO opportunity_report (opportunity_id, reporter_user_id, reason)
VALUES (14, 5, 'other');

-- [IC-17] STORED PROCEDURE rule (not_owner): Daniel tries to decide an application
--   for Priya's opportunity.
CALL sp_decide_application(9, 3, 'accepted');

-- [IC-18] STORED PROCEDURE rule (badge_requirement_not_met): "50 Verified Hours"
--   for a contributor with 5 hours.
CALL sp_award_badge(5, 3);

ROLLBACK;

-- [OP-22] After ROLLBACK: the dataset is exactly as loaded (same counts as
--   04_verify_database.sql), so this file can be run again.
SELECT (SELECT COUNT(*) FROM opportunity) AS opportunities,
       (SELECT COUNT(*) FROM application) AS applications,
       (SELECT COUNT(*) FROM work_submission) AS submissions,
       (SELECT COUNT(*) FROM point_transaction) AS ledger_rows,
       (SELECT COUNT(*) FROM opportunity_report) AS reports,
       (SELECT status FROM opportunity WHERE opportunity_id = 4) AS opportunity_4_status;
