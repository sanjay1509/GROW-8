-- =============================================================================
-- GROW8 - ENSF 608 implementation, step 4: check what was created and loaded.
-- Read-only. Run it after steps 0-3 against the same database.
-- =============================================================================

-- Database objects: expected 21 tables, 5 views, 21 triggers, 10 procedures.
SELECT 'tables' AS object_type, COUNT(*) AS created
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
UNION ALL
SELECT 'views', COUNT(*) FROM information_schema.views WHERE table_schema = DATABASE()
UNION ALL
SELECT 'triggers', COUNT(*) FROM information_schema.triggers WHERE trigger_schema = DATABASE()
UNION ALL
SELECT 'procedures', COUNT(*) FROM information_schema.routines
WHERE routine_schema = DATABASE() AND routine_type = 'PROCEDURE'
UNION ALL
SELECT 'primary keys', COUNT(*) FROM information_schema.table_constraints
WHERE constraint_schema = DATABASE() AND constraint_type = 'PRIMARY KEY'
UNION ALL
SELECT 'foreign keys', COUNT(*) FROM information_schema.table_constraints
WHERE constraint_schema = DATABASE() AND constraint_type = 'FOREIGN KEY'
UNION ALL
SELECT 'unique keys', COUNT(*) FROM information_schema.table_constraints
WHERE constraint_schema = DATABASE() AND constraint_type = 'UNIQUE'
UNION ALL
SELECT 'check constraints', COUNT(*) FROM information_schema.table_constraints
WHERE constraint_schema = DATABASE() AND constraint_type = 'CHECK';

-- Rows loaded per table (the dataset used by the operations and tests).
SELECT 'user_account' AS table_name, COUNT(*) AS row_count FROM user_account
UNION ALL SELECT 'contributor_profile',   COUNT(*) FROM contributor_profile
UNION ALL SELECT 'contributor_resume',    COUNT(*) FROM contributor_resume
UNION ALL SELECT 'creator_organization',  COUNT(*) FROM creator_organization
UNION ALL SELECT 'opportunity_category',  COUNT(*) FROM opportunity_category
UNION ALL SELECT 'skill',                 COUNT(*) FROM skill
UNION ALL SELECT 'opportunity',           COUNT(*) FROM opportunity
UNION ALL SELECT 'opportunity_skill',     COUNT(*) FROM opportunity_skill
UNION ALL SELECT 'contributor_skill',     COUNT(*) FROM contributor_skill
UNION ALL SELECT 'notification',          COUNT(*) FROM notification
UNION ALL SELECT 'application',           COUNT(*) FROM application
UNION ALL SELECT 'work_submission',       COUNT(*) FROM work_submission
UNION ALL SELECT 'submission_attachment', COUNT(*) FROM submission_attachment
UNION ALL SELECT 'work_verification',     COUNT(*) FROM work_verification
UNION ALL SELECT 'feedback',              COUNT(*) FROM feedback
UNION ALL SELECT 'admin_review',          COUNT(*) FROM admin_review
UNION ALL SELECT 'opportunity_report',    COUNT(*) FROM opportunity_report
UNION ALL SELECT 'report_review',         COUNT(*) FROM report_review
UNION ALL SELECT 'badge',                 COUNT(*) FROM badge
UNION ALL SELECT 'contributor_badge',     COUNT(*) FROM contributor_badge
UNION ALL SELECT 'point_transaction',     COUNT(*) FROM point_transaction;
