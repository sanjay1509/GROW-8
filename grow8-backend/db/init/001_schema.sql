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
    CONSTRAINT fk_point_transaction_badge
        FOREIGN KEY (badge_id) REFERENCES badge (badge_id),
    CONSTRAINT chk_point_transaction_source CHECK (
        (source = 'work_verified' AND verification_id IS NOT NULL AND badge_id IS NULL)
        OR (source = 'badge_awarded' AND badge_id IS NOT NULL AND verification_id IS NULL)
    )
) ENGINE = InnoDB;
