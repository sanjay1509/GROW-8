-- =============================================================================
-- GROW8 schema (MySQL 8.4) - single source of truth.
-- ORM models in shared/grow8_common/models/ mirror this file exactly.
--
-- Runs automatically the first time MySQL starts with an empty data volume.
-- After editing: `make reset-db` (WIPES all local MySQL data).
--
-- Conventions: INT UNSIGNED surrogate keys, DATETIME values stored in UTC,
-- status values as ENUMs, derived values (verified hours, ratings, leaderboard
-- totals) are computed by queries and never stored.
--
-- Layout: tables, then integrity triggers (rules a foreign key or CHECK cannot
-- express), then views for the derived values. Rationale for each rule:
-- docs/db/relationship-validation.md. The trigger section uses DELIMITER, which
-- the mysql client and the test loader (api/tests/conftest.py) both understand.
-- =============================================================================

SET NAMES utf8mb4;

-- -----------------------------------------------------------------------------
-- Users and profiles
-- -----------------------------------------------------------------------------

CREATE TABLE user_account (
    user_id       INT UNSIGNED NOT NULL AUTO_INCREMENT,
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('creator', 'contributor', 'admin') NOT NULL,
    full_name     VARCHAR(150) NOT NULL,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_user_account_email (email),
    KEY ix_user_account_role (role)
) ENGINE = InnoDB;

CREATE TABLE contributor_profile (
    user_id     INT UNSIGNED NOT NULL,
    headline    VARCHAR(150) NULL,
    bio         TEXT         NULL,
    institution VARCHAR(150) NULL,
    city        VARCHAR(100) NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_contributor_profile_user
        FOREIGN KEY (user_id) REFERENCES user_account (user_id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE creator_organization (
    organization_id   INT UNSIGNED NOT NULL AUTO_INCREMENT,
    owner_user_id     INT UNSIGNED NOT NULL,
    name              VARCHAR(150) NOT NULL,
    organization_type ENUM('small_business', 'nonprofit', 'event_organizer', 'other') NOT NULL,
    description       TEXT         NULL,
    website           VARCHAR(255) NULL,
    city              VARCHAR(100) NULL,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id),
    -- MVP: one organization per creator account
    UNIQUE KEY uq_creator_organization_owner (owner_user_id),
    CONSTRAINT fk_creator_organization_owner
        FOREIGN KEY (owner_user_id) REFERENCES user_account (user_id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- Reference data
-- -----------------------------------------------------------------------------

CREATE TABLE opportunity_category (
    category_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    code        VARCHAR(30)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(255) NULL,
    PRIMARY KEY (category_id),
    UNIQUE KEY uq_opportunity_category_code (code),
    UNIQUE KEY uq_opportunity_category_name (name)
) ENGINE = InnoDB;

CREATE TABLE skill (
    skill_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    code     VARCHAR(50)  NOT NULL,
    name     VARCHAR(100) NOT NULL,
    PRIMARY KEY (skill_id),
    UNIQUE KEY uq_skill_code (code),
    UNIQUE KEY uq_skill_name (name)
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- Opportunities
-- -----------------------------------------------------------------------------

CREATE TABLE opportunity (
    opportunity_id        INT UNSIGNED NOT NULL AUTO_INCREMENT,
    organization_id       INT UNSIGNED NOT NULL,
    category_id           INT UNSIGNED NOT NULL,
    title                 VARCHAR(200) NOT NULL,
    description           TEXT         NOT NULL,
    requirements          TEXT         NULL,
    location              VARCHAR(255) NULL,
    work_mode             ENUM('on_site', 'remote', 'hybrid') NULL,
    start_date            DATE         NULL,
    end_date              DATE         NULL,
    expected_hours        DECIMAL(6, 2) NULL,
    compensation_type     ENUM('paid', 'stipend', 'unpaid') NULL,
    compensation_amount   DECIMAL(10, 2) NULL,
    compensation_details  VARCHAR(500) NULL,
    applicant_limit       SMALLINT UNSIGNED NULL,
    application_deadline  DATETIME     NULL,
    working_conditions    TEXT         NULL,
    safety_information    TEXT         NULL,
    accessibility_details TEXT         NULL,
    status                ENUM('draft', 'open', 'closed', 'cancelled') NOT NULL DEFAULT 'draft',
    published_at          DATETIME     NULL,
    created_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (opportunity_id),
    KEY ix_opportunity_status_deadline (status, application_deadline),
    KEY ix_opportunity_category_status (category_id, status),
    KEY ix_opportunity_organization_status (organization_id, status),
    KEY ix_opportunity_published_at (published_at),
    CONSTRAINT fk_opportunity_organization
        FOREIGN KEY (organization_id) REFERENCES creator_organization (organization_id),
    CONSTRAINT fk_opportunity_category
        FOREIGN KEY (category_id) REFERENCES opportunity_category (category_id),
    CONSTRAINT chk_opportunity_expected_hours CHECK (expected_hours > 0),
    CONSTRAINT chk_opportunity_compensation_amount CHECK (compensation_amount >= 0),
    CONSTRAINT chk_opportunity_applicant_limit CHECK (applicant_limit > 0),
    CONSTRAINT chk_opportunity_dates CHECK (end_date >= start_date),
    -- Drafts may be incomplete; anything published must carry every mandatory disclosure.
    CONSTRAINT chk_opportunity_published_complete CHECK (
        status = 'draft' OR (
            requirements IS NOT NULL
            AND start_date IS NOT NULL
            AND end_date IS NOT NULL
            AND expected_hours IS NOT NULL
            AND compensation_type IS NOT NULL
            AND (compensation_type = 'unpaid' OR compensation_amount IS NOT NULL)
            AND applicant_limit IS NOT NULL
            AND application_deadline IS NOT NULL
            AND working_conditions IS NOT NULL
            AND safety_information IS NOT NULL
            AND accessibility_details IS NOT NULL
            AND published_at IS NOT NULL
        )
    )
) ENGINE = InnoDB;

CREATE TABLE opportunity_skill (
    opportunity_id INT UNSIGNED NOT NULL,
    skill_id       INT UNSIGNED NOT NULL,
    PRIMARY KEY (opportunity_id, skill_id),
    KEY ix_opportunity_skill_skill (skill_id),
    CONSTRAINT fk_opportunity_skill_opportunity
        FOREIGN KEY (opportunity_id) REFERENCES opportunity (opportunity_id) ON DELETE CASCADE,
    CONSTRAINT fk_opportunity_skill_skill
        FOREIGN KEY (skill_id) REFERENCES skill (skill_id)
) ENGINE = InnoDB;

CREATE TABLE contributor_skill (
    contributor_id INT UNSIGNED NOT NULL,
    skill_id       INT UNSIGNED NOT NULL,
    source         ENUM('self_reported', 'verified') NOT NULL DEFAULT 'self_reported',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contributor_id, skill_id),
    KEY ix_contributor_skill_skill (skill_id),
    CONSTRAINT fk_contributor_skill_contributor
        FOREIGN KEY (contributor_id) REFERENCES contributor_profile (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_contributor_skill_skill
        FOREIGN KEY (skill_id) REFERENCES skill (skill_id)
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- Notifications (written by the consumer services, read through the API)
-- -----------------------------------------------------------------------------

-- title/message are what the user was told at the time, kept as written even if
-- the opportunity changes later. One row per user per event: the consumers insert
-- with INSERT IGNORE, so a redelivered event adds nothing.
CREATE TABLE notification (
    notification_id   INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id           INT UNSIGNED NOT NULL,
    event_id          CHAR(36)     NOT NULL,
    notification_type ENUM('opportunity_created', 'opportunity_published') NOT NULL,
    title             VARCHAR(200) NOT NULL,
    message           VARCHAR(500) NOT NULL,
    opportunity_id    INT UNSIGNED NULL,
    read_at           DATETIME     NULL,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (notification_id),
    UNIQUE KEY uq_notification_event_user (event_id, user_id),
    -- inbox: a user's unread first, newest first; also serves the user_id FK
    KEY ix_notification_user_read_created (user_id, read_at, created_at),
    CONSTRAINT fk_notification_user
        FOREIGN KEY (user_id) REFERENCES user_account (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_opportunity
        FOREIGN KEY (opportunity_id) REFERENCES opportunity (opportunity_id) ON DELETE SET NULL
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- Applications, submissions, verification
-- -----------------------------------------------------------------------------

CREATE TABLE application (
    application_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    opportunity_id INT UNSIGNED NOT NULL,
    contributor_id INT UNSIGNED NOT NULL,
    status         ENUM('pending', 'accepted', 'rejected', 'withdrawn') NOT NULL DEFAULT 'pending',
    motivation     TEXT     NULL,
    submitted_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at     DATETIME NULL,
    PRIMARY KEY (application_id),
    UNIQUE KEY uq_application_contributor_opportunity (contributor_id, opportunity_id),
    KEY ix_application_opportunity_status (opportunity_id, status),
    CONSTRAINT fk_application_opportunity
        FOREIGN KEY (opportunity_id) REFERENCES opportunity (opportunity_id),
    CONSTRAINT fk_application_contributor
        FOREIGN KEY (contributor_id) REFERENCES contributor_profile (user_id),
    CONSTRAINT chk_application_decided
        CHECK (status IN ('pending', 'withdrawn') OR decided_at IS NOT NULL)
) ENGINE = InnoDB;

CREATE TABLE work_submission (
    submission_id  INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    application_id INT UNSIGNED  NOT NULL,
    description    TEXT          NOT NULL,
    hours_claimed  DECIMAL(6, 2) NOT NULL,
    submitted_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (submission_id),
    -- MVP: at most one submission per application
    UNIQUE KEY uq_work_submission_application (application_id),
    CONSTRAINT fk_work_submission_application
        FOREIGN KEY (application_id) REFERENCES application (application_id),
    CONSTRAINT chk_work_submission_hours CHECK (hours_claimed > 0)
) ENGINE = InnoDB;

-- Files live outside MySQL; only metadata and the storage key are kept here.
CREATE TABLE submission_attachment (
    attachment_id INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    submission_id INT UNSIGNED    NOT NULL,
    file_name     VARCHAR(255)    NOT NULL,
    content_type  VARCHAR(100)    NOT NULL,
    size_bytes    BIGINT UNSIGNED NOT NULL,
    storage_key   VARCHAR(512)    NOT NULL,
    uploaded_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attachment_id),
    UNIQUE KEY uq_submission_attachment_storage_key (storage_key),
    KEY ix_submission_attachment_submission (submission_id),
    CONSTRAINT fk_submission_attachment_submission
        FOREIGN KEY (submission_id) REFERENCES work_submission (submission_id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE work_verification (
    verification_id     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    submission_id       INT UNSIGNED NOT NULL,
    verified_by_user_id INT UNSIGNED NOT NULL,
    decision            ENUM('approved', 'rejected') NOT NULL,
    verified_hours      DECIMAL(6, 2) NULL,
    comment             TEXT         NULL,
    verified_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (verification_id),
    -- one verification per submission, so hours can never be counted twice
    UNIQUE KEY uq_work_verification_submission (submission_id),
    KEY ix_work_verification_verified_by (verified_by_user_id),
    CONSTRAINT fk_work_verification_submission
        FOREIGN KEY (submission_id) REFERENCES work_submission (submission_id),
    CONSTRAINT fk_work_verification_verified_by
        FOREIGN KEY (verified_by_user_id) REFERENCES user_account (user_id),
    CONSTRAINT chk_work_verification_hours CHECK (
        (decision = 'approved' AND verified_hours IS NOT NULL AND verified_hours > 0)
        OR (decision = 'rejected' AND verified_hours IS NULL)
    )
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- Feedback and moderation
-- -----------------------------------------------------------------------------

-- Feedback with no admin_review row is "pending".
CREATE TABLE feedback (
    feedback_id     INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    application_id  INT UNSIGNED     NOT NULL,
    author_user_id  INT UNSIGNED     NOT NULL,
    subject_user_id INT UNSIGNED     NOT NULL,
    rating          TINYINT UNSIGNED NOT NULL,
    comment         TEXT             NULL,
    created_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (feedback_id),
    UNIQUE KEY uq_feedback_application_author (application_id, author_user_id),
    KEY ix_feedback_author (author_user_id),
    KEY ix_feedback_subject (subject_user_id),
    CONSTRAINT fk_feedback_application
        FOREIGN KEY (application_id) REFERENCES application (application_id),
    CONSTRAINT fk_feedback_author
        FOREIGN KEY (author_user_id) REFERENCES user_account (user_id),
    CONSTRAINT fk_feedback_subject
        FOREIGN KEY (subject_user_id) REFERENCES user_account (user_id),
    CONSTRAINT chk_feedback_rating CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT chk_feedback_not_self CHECK (author_user_id <> subject_user_id)
) ENGINE = InnoDB;

CREATE TABLE admin_review (
    review_id     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    feedback_id   INT UNSIGNED NOT NULL,
    admin_user_id INT UNSIGNED NOT NULL,
    decision      ENUM('approved', 'rejected') NOT NULL,
    reason        VARCHAR(500) NULL,
    reviewed_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (review_id),
    -- each feedback is reviewed once
    UNIQUE KEY uq_admin_review_feedback (feedback_id),
    KEY ix_admin_review_admin (admin_user_id),
    CONSTRAINT fk_admin_review_feedback
        FOREIGN KEY (feedback_id) REFERENCES feedback (feedback_id),
    CONSTRAINT fk_admin_review_admin
        FOREIGN KEY (admin_user_id) REFERENCES user_account (user_id)
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- Rewards (stretch goal; schema supported from day one)
-- -----------------------------------------------------------------------------

CREATE TABLE badge (
    badge_id                INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    code                    VARCHAR(50)   NOT NULL,
    name                    VARCHAR(100)  NOT NULL,
    description             VARCHAR(255)  NULL,
    points                  INT UNSIGNED  NOT NULL DEFAULT 0,
    required_verified_hours DECIMAL(6, 2) NULL,
    PRIMARY KEY (badge_id),
    UNIQUE KEY uq_badge_code (code),
    UNIQUE KEY uq_badge_name (name)
) ENGINE = InnoDB;

CREATE TABLE contributor_badge (
    contributor_id INT UNSIGNED NOT NULL,
    badge_id       INT UNSIGNED NOT NULL,
    awarded_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contributor_id, badge_id),
    KEY ix_contributor_badge_badge (badge_id),
    CONSTRAINT fk_contributor_badge_contributor
        FOREIGN KEY (contributor_id) REFERENCES contributor_profile (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_contributor_badge_badge
        FOREIGN KEY (badge_id) REFERENCES badge (badge_id)
) ENGINE = InnoDB;

-- Leaderboard totals are SUM(points) over this table, never stored.
CREATE TABLE point_transaction (
    transaction_id  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    contributor_id  INT UNSIGNED NOT NULL,
    points          INT          NOT NULL,
    source          ENUM('work_verified', 'badge_awarded') NOT NULL,
    verification_id INT UNSIGNED NULL,
    badge_id        INT UNSIGNED NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (transaction_id),
    -- points are awarded once per verification and once per badge
    UNIQUE KEY uq_point_transaction_verification (verification_id),
    UNIQUE KEY uq_point_transaction_contributor_badge (contributor_id, badge_id),
    KEY ix_point_transaction_badge (badge_id),
    CONSTRAINT fk_point_transaction_contributor
        FOREIGN KEY (contributor_id) REFERENCES contributor_profile (user_id),
    CONSTRAINT fk_point_transaction_verification
        FOREIGN KEY (verification_id) REFERENCES work_verification (verification_id),
    -- Badge points only for a badge this contributor actually earned. Not checked
    -- when badge_id is NULL (work_verified points).
    CONSTRAINT fk_point_transaction_contributor_badge
        FOREIGN KEY (contributor_id, badge_id)
        REFERENCES contributor_badge (contributor_id, badge_id),
    CONSTRAINT chk_point_transaction_source CHECK (
        (source = 'work_verified' AND verification_id IS NOT NULL AND badge_id IS NULL)
        OR (source = 'badge_awarded' AND badge_id IS NOT NULL AND verification_id IS NULL)
    )
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- Integrity rules (triggers)
--
-- A foreign key only proves a referenced row exists, and a CHECK cannot look at
-- another table. These rules need both, so each one is a small procedure called
-- from BEFORE INSERT / BEFORE UPDATE triggers. A violation raises SQLSTATE 45000
-- (MySQL error 1644) with a message that starts with the rule name.
-- References (R1, I6, ...) are to docs/db/relationship-validation.md.
-- -----------------------------------------------------------------------------

DELIMITER $$

-- I6 (R1, R2, R15): the referenced account must have the expected role.
DROP PROCEDURE IF EXISTS grow8_require_role $$
CREATE PROCEDURE grow8_require_role(
    IN p_user_id INT UNSIGNED, IN p_role VARCHAR(20), IN p_rule VARCHAR(60))
BEGIN
    DECLARE v_role VARCHAR(20);
    DECLARE v_msg VARCHAR(128);
    SET v_role = (SELECT role FROM user_account WHERE user_id = p_user_id);
    -- a missing user is left to the foreign key
    IF v_role IS NOT NULL AND v_role <> p_role THEN
        SET v_msg = CONCAT(p_rule, ': user ', p_user_id, ' must have role ', p_role);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;
END $$

-- I6: once an account owns role-specific rows, its role can no longer change,
-- otherwise the role triggers above could be bypassed afterwards.
DROP PROCEDURE IF EXISTS grow8_require_role_change_allowed $$
CREATE PROCEDURE grow8_require_role_change_allowed(
    IN p_user_id INT UNSIGNED, IN p_old_role VARCHAR(20), IN p_new_role VARCHAR(20))
BEGIN
    IF p_old_role <> p_new_role AND (
        EXISTS (SELECT 1 FROM contributor_profile WHERE user_id = p_user_id)
        OR EXISTS (SELECT 1 FROM creator_organization WHERE owner_user_id = p_user_id)
        OR EXISTS (SELECT 1 FROM admin_review WHERE admin_user_id = p_user_id)
        OR EXISTS (SELECT 1 FROM work_verification WHERE verified_by_user_id = p_user_id)
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'role_locked: account already has rows that depend on its role';
    END IF;
END $$

-- I7 (R9): work can only be submitted for an accepted application.
DROP PROCEDURE IF EXISTS grow8_require_accepted_application $$
CREATE PROCEDURE grow8_require_accepted_application(IN p_application_id INT UNSIGNED)
BEGIN
    IF (SELECT status FROM application WHERE application_id = p_application_id)
            <> 'accepted' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'submission_requires_accepted: application is not accepted';
    END IF;
END $$

-- I7 (R9): an accepted application that already has a submission cannot leave
-- the accepted state, or the rule above would stop holding.
DROP PROCEDURE IF EXISTS grow8_require_application_status_change_allowed $$
CREATE PROCEDURE grow8_require_application_status_change_allowed(
    IN p_application_id INT UNSIGNED, IN p_old_status VARCHAR(20), IN p_new_status VARCHAR(20))
BEGIN
    IF p_old_status = 'accepted' AND p_new_status <> 'accepted'
            AND EXISTS (SELECT 1 FROM work_submission WHERE application_id = p_application_id)
    THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'submission_requires_accepted: work already submitted';
    END IF;
END $$

-- I6 (R20): only the creator who owns the opportunity's organization verifies work.
DROP PROCEDURE IF EXISTS grow8_require_verifier $$
CREATE PROCEDURE grow8_require_verifier(
    IN p_submission_id INT UNSIGNED, IN p_user_id INT UNSIGNED)
BEGIN
    DECLARE v_owner INT UNSIGNED;
    SET v_owner = (
        SELECT org.owner_user_id
        FROM work_submission ws
        JOIN application a ON a.application_id = ws.application_id
        JOIN opportunity o ON o.opportunity_id = a.opportunity_id
        JOIN creator_organization org ON org.organization_id = o.organization_id
        WHERE ws.submission_id = p_submission_id
    );
    IF v_owner IS NOT NULL AND v_owner <> p_user_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'verifier_not_owner: verifier must own the opportunity''s organization';
    END IF;
END $$

-- I2 (R13): author and subject must be the two people on the application: the
-- contributor who applied and the creator who owns the opportunity's organization.
-- (author <> subject is already chk_feedback_not_self.)
DROP PROCEDURE IF EXISTS grow8_require_feedback_participants $$
CREATE PROCEDURE grow8_require_feedback_participants(
    IN p_application_id INT UNSIGNED, IN p_author INT UNSIGNED, IN p_subject INT UNSIGNED)
BEGIN
    DECLARE v_contributor INT UNSIGNED;
    DECLARE v_owner INT UNSIGNED;
    -- SET (SELECT ...) rather than SELECT ... INTO: no "No data" warning on a miss
    SET v_contributor = (
        SELECT contributor_id FROM application WHERE application_id = p_application_id);
    SET v_owner = (
        SELECT org.owner_user_id
        FROM application a
        JOIN opportunity o ON o.opportunity_id = a.opportunity_id
        JOIN creator_organization org ON org.organization_id = o.organization_id
        WHERE a.application_id = p_application_id);
    IF v_contributor IS NOT NULL AND (
        p_author NOT IN (v_contributor, v_owner) OR p_subject NOT IN (v_contributor, v_owner)
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'feedback_participants: author and subject must be on the application';
    END IF;
END $$

-- I7 (R18) and I3: verification points come only from an approved verification
-- of this same contributor's work. (Badge points are checked by
-- fk_point_transaction_contributor_badge.)
DROP PROCEDURE IF EXISTS grow8_require_point_source $$
CREATE PROCEDURE grow8_require_point_source(
    IN p_contributor_id INT UNSIGNED, IN p_verification_id INT UNSIGNED)
BEGIN
    DECLARE v_decision VARCHAR(20);
    DECLARE v_contributor INT UNSIGNED;
    IF p_verification_id IS NOT NULL THEN
        SET v_decision = (
            SELECT decision FROM work_verification WHERE verification_id = p_verification_id);
        SET v_contributor = (
            SELECT a.contributor_id
            FROM work_verification wv
            JOIN work_submission ws ON ws.submission_id = wv.submission_id
            JOIN application a ON a.application_id = ws.application_id
            WHERE wv.verification_id = p_verification_id);
        IF v_decision IS NOT NULL AND v_decision <> 'approved' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'points_require_approval: verification was not approved';
        END IF;
        IF v_contributor IS NOT NULL AND v_contributor <> p_contributor_id THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'points_wrong_contributor: verification belongs to another contributor';
        END IF;
    END IF;
END $$

CREATE TRIGGER trg_user_account_bu BEFORE UPDATE ON user_account FOR EACH ROW
    CALL grow8_require_role_change_allowed(OLD.user_id, OLD.role, NEW.role) $$

CREATE TRIGGER trg_contributor_profile_bi BEFORE INSERT ON contributor_profile FOR EACH ROW
    CALL grow8_require_role(NEW.user_id, 'contributor', 'contributor_profile_role') $$
CREATE TRIGGER trg_contributor_profile_bu BEFORE UPDATE ON contributor_profile FOR EACH ROW
    CALL grow8_require_role(NEW.user_id, 'contributor', 'contributor_profile_role') $$

CREATE TRIGGER trg_creator_organization_bi BEFORE INSERT ON creator_organization FOR EACH ROW
    CALL grow8_require_role(NEW.owner_user_id, 'creator', 'organization_owner_role') $$
CREATE TRIGGER trg_creator_organization_bu BEFORE UPDATE ON creator_organization FOR EACH ROW
    CALL grow8_require_role(NEW.owner_user_id, 'creator', 'organization_owner_role') $$

CREATE TRIGGER trg_application_bu BEFORE UPDATE ON application FOR EACH ROW
    CALL grow8_require_application_status_change_allowed(
        OLD.application_id, OLD.status, NEW.status) $$

CREATE TRIGGER trg_work_submission_bi BEFORE INSERT ON work_submission FOR EACH ROW
    CALL grow8_require_accepted_application(NEW.application_id) $$
CREATE TRIGGER trg_work_submission_bu BEFORE UPDATE ON work_submission FOR EACH ROW
    CALL grow8_require_accepted_application(NEW.application_id) $$

CREATE TRIGGER trg_work_verification_bi BEFORE INSERT ON work_verification FOR EACH ROW
    CALL grow8_require_verifier(NEW.submission_id, NEW.verified_by_user_id) $$
CREATE TRIGGER trg_work_verification_bu BEFORE UPDATE ON work_verification FOR EACH ROW
    CALL grow8_require_verifier(NEW.submission_id, NEW.verified_by_user_id) $$

CREATE TRIGGER trg_feedback_bi BEFORE INSERT ON feedback FOR EACH ROW
    CALL grow8_require_feedback_participants(
        NEW.application_id, NEW.author_user_id, NEW.subject_user_id) $$
CREATE TRIGGER trg_feedback_bu BEFORE UPDATE ON feedback FOR EACH ROW
    CALL grow8_require_feedback_participants(
        NEW.application_id, NEW.author_user_id, NEW.subject_user_id) $$

CREATE TRIGGER trg_admin_review_bi BEFORE INSERT ON admin_review FOR EACH ROW
    CALL grow8_require_role(NEW.admin_user_id, 'admin', 'reviewer_role') $$
CREATE TRIGGER trg_admin_review_bu BEFORE UPDATE ON admin_review FOR EACH ROW
    CALL grow8_require_role(NEW.admin_user_id, 'admin', 'reviewer_role') $$

CREATE TRIGGER trg_point_transaction_bi BEFORE INSERT ON point_transaction FOR EACH ROW
    CALL grow8_require_point_source(NEW.contributor_id, NEW.verification_id) $$
CREATE TRIGGER trg_point_transaction_bu BEFORE UPDATE ON point_transaction FOR EACH ROW
    CALL grow8_require_point_source(NEW.contributor_id, NEW.verification_id) $$

DELIMITER ;

-- -----------------------------------------------------------------------------
-- Derived values (views) - I1, I3
--
-- Verified hours, ratings, feedback status and leaderboard totals are calculated
-- from the underlying records every time, so they can never drift from them.
-- -----------------------------------------------------------------------------

-- I1: a feedback's status is derived from its review, never stored twice.
CREATE OR REPLACE VIEW v_feedback_status AS
SELECT f.feedback_id,
       f.application_id,
       f.author_user_id,
       f.subject_user_id,
       f.rating,
       COALESCE(ar.decision, 'pending') AS status,
       ar.reviewed_at
FROM feedback f
LEFT JOIN admin_review ar ON ar.feedback_id = f.feedback_id;

-- Approved hours and completed opportunities per contributor (0 when none yet).
CREATE OR REPLACE VIEW v_contributor_verified_hours AS
SELECT cp.user_id AS contributor_id,
       COALESCE(SUM(wv.verified_hours), 0) AS verified_hours,
       COUNT(wv.verification_id) AS completed_opportunities
FROM contributor_profile cp
LEFT JOIN application a ON a.contributor_id = cp.user_id
LEFT JOIN work_submission ws ON ws.application_id = a.application_id
LEFT JOIN work_verification wv
       ON wv.submission_id = ws.submission_id AND wv.decision = 'approved'
GROUP BY cp.user_id;

-- Public rating: only feedback an admin approved counts. With one organization
-- per creator (uq_creator_organization_owner) a creator's rating is also their
-- organization's rating.
CREATE OR REPLACE VIEW v_user_rating AS
SELECT f.subject_user_id AS user_id,
       ROUND(AVG(f.rating), 2) AS average_rating,
       COUNT(*) AS approved_feedback_count
FROM feedback f
JOIN admin_review ar ON ar.feedback_id = f.feedback_id AND ar.decision = 'approved'
GROUP BY f.subject_user_id;

-- All-time leaderboard of active contributors. For a period, filter
-- point_transaction.created_at in the query instead.
CREATE OR REPLACE VIEW v_leaderboard AS
SELECT cp.user_id AS contributor_id,
       ua.full_name,
       COALESCE(SUM(pt.points), 0) AS total_points,
       RANK() OVER (ORDER BY COALESCE(SUM(pt.points), 0) DESC) AS leaderboard_rank
FROM contributor_profile cp
JOIN user_account ua ON ua.user_id = cp.user_id AND ua.is_active = TRUE
LEFT JOIN point_transaction pt ON pt.contributor_id = cp.user_id
GROUP BY cp.user_id, ua.full_name;
