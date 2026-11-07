-- =============================================================================
-- GROW8 workflow seed data - DEVELOPMENT ONLY. Never load this into a real deployment.
--
-- Runs after 002_seed.sql on first MySQL start (re-run with `make reset-db`).
-- 002 stops at opportunities; this file adds a believable history on top of it so
-- every table and every view returns data:
--
--   application -> work_submission -> work_verification -> point_transaction
--                                                       -> contributor_badge
--   application -> feedback -> admin_review
--
-- Fixed IDs and fixed dates (UTC), like 002. Every row passes the integrity
-- triggers in 001_schema.sql: applications are dated before each deadline and
-- within each applicant limit, verifiers own the opportunity, feedback is between
-- the two people on the application, and points come only from approved work or
-- an earned badge.
--
-- Points rule used here: 10 points per verified hour, plus the badge's points.
--
-- The API integration tests do not load this file; they start from 002 only.
-- =============================================================================

SET NAMES utf8mb4;

-- -----------------------------------------------------------------------------
-- Opportunity 11 (Summer BBQ, closed) took its applications in July, while it was
-- open. Re-open it for the insert so the replayed history passes the
-- "apply only while open" rule, then close it again.
-- -----------------------------------------------------------------------------

UPDATE opportunity SET status = 'open' WHERE opportunity_id = 11;

-- -----------------------------------------------------------------------------
-- Applications
-- Contributors: 5 Alex Chen, 6 Jordan Lee, 7 Sam Patel.
-- Inactive rows (rejected, withdrawn) are inserted with their final status, which
-- takes no place under the applicant limit.
-- -----------------------------------------------------------------------------

INSERT INTO application (application_id, opportunity_id, contributor_id, status, motivation, submitted_at, decided_at) VALUES
-- Opportunity 11, Summer BBQ (food bank, creator 3): completed in August
(1, 11, 6, 'accepted',  'I have my food handler certificate and love community events.', '2026-07-10 16:00:00', '2026-07-15 15:00:00'),
(2, 11, 5, 'accepted',  'Happy to help serve and clean up.',                          '2026-07-12 18:30:00', '2026-07-15 15:05:00'),
(3, 11, 7, 'rejected',  'Can bring my camera too.',                                   '2026-07-20 20:00:00', '2026-07-25 14:00:00'),
-- Opportunity 10, Warehouse inventory count (food bank, creator 3): done mid-October
(4, 10, 6, 'accepted',  'Done stock counts at my part-time retail job.',              '2026-10-02 17:00:00', '2026-10-05 16:00:00'),
(5, 10, 7, 'accepted',  'Detail-oriented and available both days.',                   '2026-10-03 19:00:00', '2026-10-05 16:10:00'),
(6, 10, 5, 'accepted',  'Want to try a hands-on volunteer role.',                     '2026-10-04 21:00:00', '2026-10-05 16:20:00'),
-- Opportunity 5, Weekend food hamper packing (food bank): starts in December
(7, 5, 6,  'accepted',  'Available every Saturday morning.',                          '2026-10-15 15:00:00', '2026-10-17 15:00:00'),
-- Opportunity 12, Fun run photographer (YYC events, creator 4): event on Nov 15
(8, 12, 7, 'accepted',  'Portfolio: example.com/sam-photo',                           '2026-10-20 18:00:00', '2026-10-22 17:00:00'),
-- Opportunity 3, Social media calendar (bakery, creator 2): still deciding
(9, 3, 7,  'pending',   'Built content calendars for two student clubs.',            '2026-10-25 20:00:00', NULL),
(10, 3, 5, 'withdrawn', 'Interested in learning social media planning.',              '2026-10-26 22:00:00', NULL),
-- Opportunity 2, Inventory spreadsheet cleanup (bakery, limit 1): one place, taken
(11, 2, 6, 'rejected',  'Comfortable with spreadsheets.',                             '2026-10-27 16:00:00', '2026-10-29 15:00:00'),
(12, 2, 5, 'accepted',  'I clean data in pandas and Excel for my courses.',           '2026-10-28 17:00:00', '2026-10-30 15:00:00'),
-- Opportunity 1, Digitize recipe archive (bakery, limit 2): full, both pending
(13, 1, 6, 'pending',   'Fast and accurate typist.',                                  '2026-11-02 18:00:00', NULL),
(14, 1, 7, 'pending',   'Would love to help preserve the recipes.',                   '2026-11-03 19:00:00', NULL);

UPDATE opportunity SET status = 'closed' WHERE opportunity_id = 11;

-- -----------------------------------------------------------------------------
-- Work submissions (only for accepted applications)
-- -----------------------------------------------------------------------------

INSERT INTO work_submission (submission_id, application_id, description, hours_claimed, submitted_at) VALUES
(1, 1, 'Served food and cleaned up the BBQ site; full afternoon shift.',        6.00, '2026-08-11 15:00:00'),
(2, 2, 'Served food for the first half, then packed leftovers.',                5.50, '2026-08-11 18:00:00'),
(3, 4, 'Counted aisles A to D both days; count sheets uploaded.',               8.00, '2026-10-17 16:00:00'),
(4, 5, 'Counted aisles E to H both days.',                                      8.00, '2026-10-17 17:00:00'),
(5, 6, 'Helped recount the cold storage on day two.',                           8.00, '2026-10-18 15:00:00');

INSERT INTO submission_attachment (attachment_id, submission_id, file_name, content_type, size_bytes, storage_key, uploaded_at) VALUES
(1, 3, 'count-sheets-aisles-a-d.pdf', 'application/pdf', 482113, 'dev/submissions/3/count-sheets-aisles-a-d.pdf', '2026-10-17 16:00:00'),
(2, 5, 'cold-storage-recount.xlsx',   'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 23855, 'dev/submissions/5/cold-storage-recount.xlsx', '2026-10-18 15:00:00');

-- -----------------------------------------------------------------------------
-- Verifications by the creator who owns the opportunity (food bank, creator 3).
-- Submission 5 (Alex, warehouse) is still awaiting verification.
-- -----------------------------------------------------------------------------

INSERT INTO work_verification (verification_id, submission_id, verified_by_user_id, decision, verified_hours, comment, verified_at) VALUES
(1, 1, 3, 'approved', 6.00, 'Great with the families, thank you!',                     '2026-08-12 16:00:00'),
(2, 2, 3, 'approved', 5.00, 'Left half an hour early, so 5 hours verified.',           '2026-08-12 16:10:00'),
(3, 3, 3, 'approved', 8.00, 'Count sheets match our system.',                          '2026-10-19 15:00:00'),
(4, 4, 3, 'rejected', NULL, 'No count sheets were uploaded, so the hours cannot be verified.', '2026-10-19 15:30:00');

-- -----------------------------------------------------------------------------
-- Badges earned (badge criteria from 002: 1 first verified task, 2 ten verified
-- hours, 4 a verified community opportunity)
-- -----------------------------------------------------------------------------

INSERT INTO contributor_badge (contributor_id, badge_id, awarded_at) VALUES
(6, 1, '2026-08-12 16:00:00'),  -- Jordan: first verified task (BBQ)
(6, 4, '2026-08-12 16:00:00'),  -- Jordan: community helper (BBQ is a community opportunity)
(5, 1, '2026-08-12 16:10:00'),  -- Alex: first verified task (BBQ)
(5, 4, '2026-08-12 16:10:00'),  -- Alex: community helper
(6, 2, '2026-10-19 15:00:00');  -- Jordan: 6 + 8 = 14 verified hours

-- -----------------------------------------------------------------------------
-- Points ledger (the leaderboard is SUM(points); nothing is stored as a total)
-- -----------------------------------------------------------------------------

INSERT INTO point_transaction (transaction_id, contributor_id, points, source, verification_id, badge_id, created_at) VALUES
(1, 6, 60, 'work_verified', 1, NULL, '2026-08-12 16:00:00'),
(2, 6, 10, 'badge_awarded', NULL, 1, '2026-08-12 16:00:00'),
(3, 6, 20, 'badge_awarded', NULL, 4, '2026-08-12 16:00:00'),
(4, 5, 50, 'work_verified', 2, NULL, '2026-08-12 16:10:00'),
(5, 5, 10, 'badge_awarded', NULL, 1, '2026-08-12 16:10:00'),
(6, 5, 20, 'badge_awarded', NULL, 4, '2026-08-12 16:10:00'),
(7, 6, 80, 'work_verified', 3, NULL, '2026-10-19 15:00:00'),
(8, 6, 25, 'badge_awarded', NULL, 2, '2026-10-19 15:00:00');

-- -----------------------------------------------------------------------------
-- Feedback between the contributor and the creator on each application, and the
-- admin's moderation. No admin_review row means the feedback is still pending.
-- -----------------------------------------------------------------------------

INSERT INTO feedback (feedback_id, application_id, author_user_id, subject_user_id, rating, comment, reports_discrepancy, created_at) VALUES
(1, 1, 6, 3, 5, 'Well organized and very welcoming.',                                  FALSE, '2026-08-13 15:00:00'),
(2, 1, 3, 6, 5, 'Reliable and great with the public.',                                 FALSE, '2026-08-13 16:00:00'),
(3, 2, 5, 3, 4, 'Good event, the briefing could have been earlier.',                    FALSE, '2026-08-14 15:00:00'),
(4, 2, 3, 5, 4, 'Helpful; call me on 403-555-0199 if you want more shifts.',            FALSE, '2026-08-14 16:00:00'),
(5, 5, 7, 3, 1, 'I worked both days but my hours were rejected. The count sheets were handed in on paper.', TRUE, '2026-10-20 15:00:00'),
(6, 4, 6, 3, 3, 'Fine, but the warehouse was very cold.',                               FALSE, '2026-10-20 16:00:00'),
(7, 3, 7, 3, 2, 'Rejected without any reason given.',                                   TRUE, '2026-07-26 15:00:00');

INSERT INTO admin_review (review_id, feedback_id, admin_user_id, decision, reason, reviewed_at) VALUES
(1, 1, 1, 'approved', NULL,                                              '2026-08-14 15:00:00'),
(2, 2, 1, 'approved', NULL,                                              '2026-08-14 15:05:00'),
(3, 3, 1, 'approved', NULL,                                              '2026-08-15 15:00:00'),
(4, 4, 1, 'rejected', 'Contains personal contact details.',             '2026-08-15 15:05:00'),
(5, 7, 1, 'rejected', 'Selection decisions are at the creator''s discretion.', '2026-07-28 15:00:00');
