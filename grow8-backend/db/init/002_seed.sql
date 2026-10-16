-- =============================================================================
-- GROW8 seed data - DEVELOPMENT ONLY. Never load this into a real deployment.
--
-- Fixed IDs and fixed dates so every developer gets an identical database.
-- Runs after 001_schema.sql on first MySQL start; re-run with `make reset-db`.
--
-- All seeded accounts share the dev password:  Grow8Dev!2026
-- =============================================================================

SET NAMES utf8mb4;

-- -----------------------------------------------------------------------------
-- Reference data
-- -----------------------------------------------------------------------------

INSERT INTO opportunity_category (category_id, code, name, description) VALUES
    (1, 'knowledge', 'Knowledge-based', 'Digital support, data organization, record digitization and similar tasks.'),
    (2, 'community', 'Community', 'Physical tasks, community activities and event-based support.');

INSERT INTO skill (skill_id, code, name) VALUES
    (1,  'data-entry',       'Data entry'),
    (2,  'spreadsheets',     'Spreadsheets'),
    (3,  'data-cleaning',    'Data cleaning'),
    (4,  'social-media',     'Social media'),
    (5,  'graphic-design',   'Graphic design'),
    (6,  'web-basics',       'Web basics (HTML/CSS)'),
    (7,  'customer-service', 'Customer service'),
    (8,  'event-setup',      'Event setup'),
    (9,  'food-handling',    'Food handling'),
    (10, 'inventory',        'Inventory management'),
    (11, 'photography',      'Photography'),
    (12, 'translation',      'Translation');

INSERT INTO badge (badge_id, code, name, description, points, required_verified_hours) VALUES
    (1, 'first-verified',   'First Verified Task', 'Completed and verified a first opportunity.', 10,  NULL),
    (2, 'ten-hours',        '10 Verified Hours',   'Reached 10 verified hours.',                  25,  10.00),
    (3, 'fifty-hours',      '50 Verified Hours',   'Reached 50 verified hours.',                  100, 50.00),
    (4, 'community-helper', 'Community Helper',    'Completed a verified community opportunity.', 20,  NULL);

-- -----------------------------------------------------------------------------
-- Users (DEV ONLY) - password for all: Grow8Dev!2026
-- -----------------------------------------------------------------------------

INSERT INTO user_account (user_id, email, password_hash, role, full_name) VALUES
    (1, 'admin@grow8.dev',        '$2b$12$a8YZn.bGHfAHW8/Cnlx79O0xINuQd4A/E33BxLnujHoSNljsRTacW', 'admin',       'Ada Admin'),
    (2, 'maple.bakery@grow8.dev', '$2b$12$a8YZn.bGHfAHW8/Cnlx79O0xINuQd4A/E33BxLnujHoSNljsRTacW', 'creator',     'Priya Nair'),
    (3, 'foodbank@grow8.dev',     '$2b$12$a8YZn.bGHfAHW8/Cnlx79O0xINuQd4A/E33BxLnujHoSNljsRTacW', 'creator',     'Daniel Okafor'),
    (4, 'yyc.events@grow8.dev',   '$2b$12$a8YZn.bGHfAHW8/Cnlx79O0xINuQd4A/E33BxLnujHoSNljsRTacW', 'creator',     'Sofia Martinez'),
    (5, 'alex.chen@grow8.dev',    '$2b$12$a8YZn.bGHfAHW8/Cnlx79O0xINuQd4A/E33BxLnujHoSNljsRTacW', 'contributor', 'Alex Chen'),
    (6, 'jordan.lee@grow8.dev',   '$2b$12$a8YZn.bGHfAHW8/Cnlx79O0xINuQd4A/E33BxLnujHoSNljsRTacW', 'contributor', 'Jordan Lee'),
    (7, 'sam.patel@grow8.dev',    '$2b$12$a8YZn.bGHfAHW8/Cnlx79O0xINuQd4A/E33BxLnujHoSNljsRTacW', 'contributor', 'Sam Patel');

INSERT INTO creator_organization (organization_id, owner_user_id, name, organization_type, description, website, city) VALUES
    (1, 2, 'Maple Street Bakery',            'small_business',  'Family-run neighbourhood bakery.',                         'https://example.com/maple-street-bakery', 'Calgary'),
    (2, 3, 'Bow River Community Food Bank',  'nonprofit',       'Food bank serving families across north-east Calgary.',    'https://example.com/bow-river-food-bank', 'Calgary'),
    (3, 4, 'YYC Neighbourhood Events',       'event_organizer', 'Volunteer-driven organizer of free community events.',     'https://example.com/yyc-events',          'Calgary');

INSERT INTO contributor_profile (user_id, headline, bio, institution, city) VALUES
    (5, 'Software engineering student',  'Second-year student looking for real project experience.', 'University of Calgary', 'Calgary'),
    (6, 'Business administration student', 'Interested in nonprofits and community work.',           'Mount Royal University', 'Calgary'),
    (7, 'Early-career designer',         'Recent graduate building a design portfolio.',               'SAIT',                   'Calgary');

INSERT INTO contributor_skill (contributor_id, skill_id, source) VALUES
    (5, 2, 'self_reported'), (5, 3, 'self_reported'), (5, 6, 'self_reported'),
    (6, 7, 'self_reported'), (6, 8, 'self_reported'), (6, 9, 'self_reported'),
    (7, 4, 'self_reported'), (7, 5, 'self_reported'), (7, 11, 'self_reported');

-- -----------------------------------------------------------------------------
-- Opportunities (DEV ONLY placeholders)
-- Covers: both categories, every work mode and compensation type, open / closed /
-- draft statuses, one open-but-past-deadline row (10), an incomplete draft (14)
-- and a publishable draft (15). All times are UTC.
-- -----------------------------------------------------------------------------

INSERT INTO opportunity (
    opportunity_id, organization_id, category_id, title, description, requirements,
    location, work_mode, start_date, end_date, expected_hours,
    compensation_type, compensation_amount, compensation_details, applicant_limit,
    application_deadline, working_conditions, safety_information, accessibility_details,
    status, published_at, created_at
) VALUES
(1, 1, 1, 'Digitize paper recipe archive',
    'Scan and transcribe about 300 handwritten recipe cards into a structured spreadsheet.',
    'Careful typing, basic spreadsheet skills. Scanner provided on site.',
    'Calgary (Kensington)', 'hybrid', '2026-11-25', '2026-12-12', 20.00,
    'paid', 400.00, 'Flat fee, paid by e-transfer after verification.', 2,
    '2026-11-20 23:59:59', 'Flexible hours; scanning on site, transcription from home.',
    'Standard office setting; no hazards beyond normal computer use.',
    'Step-free entrance; adjustable-height desk available.',
    'open', '2026-10-01 15:00:00', '2026-09-30 18:00:00'),
(2, 1, 1, 'Inventory spreadsheet cleanup',
    'Merge three years of supplier spreadsheets into one clean inventory sheet.',
    'Comfortable with spreadsheet formulas and removing duplicates.',
    NULL, 'remote', '2026-11-10', '2026-11-24', 12.00,
    'stipend', 150.00, 'Stipend paid at completion.', 1,
    '2026-11-05 23:59:59', 'Fully remote, self-paced.',
    'Remote work; take regular screen breaks.',
    'Remote; any assistive technology you already use is fine.',
    'open', '2026-10-05 16:00:00', '2026-10-05 15:00:00'),
(3, 1, 1, 'Social media content calendar for the holiday season',
    'Plan and draft six weeks of Instagram posts, including product photos.',
    'Portfolio or examples of previous social media work.',
    'Calgary (Kensington)', 'hybrid', '2026-11-16', '2026-12-20', 15.00,
    'paid', 300.00, 'Paid in two instalments.', 2,
    '2026-11-12 23:59:59', 'Two short photo sessions in the bakery; the rest remote.',
    'Kitchen areas are hot; stay behind the counter line during photo sessions.',
    'Step-free entrance; photo sessions can be scheduled around your needs.',
    'open', '2026-10-08 17:00:00', '2026-10-08 16:00:00'),
(4, 1, 2, 'Holiday market booth assistant',
    'Help run the bakery stall at the weekend holiday market: serving, restocking and payments.',
    'Friendly with customers; food handler certificate is a plus.',
    'Calgary Farmers'' Market', 'on_site', '2026-12-05', '2026-12-20', 16.00,
    'paid', 320.00, 'Hourly equivalent of $20/h.', 3,
    '2026-12-01 23:59:59', 'Weekend shifts of 4 hours, standing at the stall.',
    'Food safety briefing on the first shift; gloves and aprons provided.',
    'Seating available behind the stall; venue is wheelchair accessible.',
    'open', '2026-10-10 15:30:00', '2026-10-10 15:00:00'),
(5, 2, 2, 'Weekend food hamper packing',
    'Pack and label food hampers for families on Saturday mornings.',
    'Able to lift boxes up to 10 kg (lighter tasks available).',
    'Calgary (Marlborough)', 'on_site', '2026-12-01', '2027-01-31', 24.00,
    'unpaid', NULL, 'Volunteer role; verified hours count toward your GROW8 record.', 10,
    '2026-11-30 23:59:59', 'Saturday 9:00-12:00 shifts in the warehouse.',
    'Closed-toe shoes required; lifting training on the first shift.',
    'Ground-floor warehouse; seated labelling tasks available.',
    'open', '2026-09-20 14:00:00', '2026-09-20 13:00:00'),
(6, 2, 1, 'Donor database deduplication',
    'Find and merge duplicate donor records in our CRM export before year-end receipts.',
    'Experience with spreadsheets or basic data cleaning; confidentiality agreement required.',
    NULL, 'remote', '2027-01-05', '2027-02-15', 30.00,
    'stipend', 250.00, 'Stipend paid on verification.', 2,
    '2026-12-15 23:59:59', 'Remote, around 5 hours per week.',
    'Remote work; personal data must stay on the provided laptop.',
    'Remote; screen-reader friendly spreadsheets on request.',
    'open', '2026-10-12 18:00:00', '2026-10-12 17:00:00'),
(7, 2, 1, 'Translate client intake forms (Spanish, Punjabi)',
    'Translate our two-page intake form and FAQ into Spanish and Punjabi.',
    'Fluent written Spanish or Punjabi.',
    NULL, 'remote', '2027-01-20', '2027-02-10', 10.00,
    'unpaid', NULL, 'Volunteer role.', 3,
    '2027-01-15 23:59:59', 'Remote, flexible schedule.',
    'Remote work; no hazards.',
    'Remote; any assistive technology you already use is fine.',
    'open', '2026-10-14 16:00:00', '2026-10-14 15:00:00'),
(8, 3, 2, 'Winter lantern festival setup crew',
    'Set up lanterns, signage and seating for a three-day winter festival.',
    'Comfortable working outdoors in winter; able to carry light equipment.',
    'Prince''s Island Park, Calgary', 'on_site', '2027-01-16', '2027-01-18', 12.00,
    'paid', 264.00, '$22/h, paid after the event.', 8,
    '2026-12-10 23:59:59', 'Outdoor shifts of 4 hours in winter conditions; warming tent on site.',
    'Winter clothing required; site safety briefing and high-visibility vests provided.',
    'Paved paths to the main site; indoor sign-making tasks available.',
    'open', '2026-10-11 19:00:00', '2026-10-11 18:00:00'),
(9, 3, 1, 'Event registration website refresh',
    'Refresh our static event registration page and make it mobile friendly.',
    'HTML/CSS basics; share a link to something you have built.',
    'Calgary (Beltline)', 'hybrid', '2026-12-01', '2027-01-10', 25.00,
    'paid', 600.00, 'Paid in two milestones.', 1,
    '2026-11-25 23:59:59', 'Mostly remote; one kickoff meeting in person.',
    'Remote work; meeting held in a public library room.',
    'Kickoff can be held online instead.',
    'open', '2026-10-03 20:00:00', '2026-10-03 19:00:00'),
(10, 2, 2, 'Warehouse inventory count',
    'Count and record stock levels before the winter drive.',
    'Attention to detail.',
    'Calgary (Marlborough)', 'on_site', '2026-10-15', '2026-10-16', 8.00,
    'unpaid', NULL, 'Volunteer role.', 6,
    '2026-10-10 23:59:59', 'Two 4-hour shifts in the warehouse.',
    'Closed-toe shoes required; no ladder work.',
    'Ground-floor warehouse.',
    'open', '2026-09-15 14:00:00', '2026-09-15 13:00:00'),
(11, 2, 2, 'Summer BBQ volunteer crew',
    'Serve food and clean up at the annual summer community BBQ.',
    'Food handler certificate preferred.',
    'Calgary (Marlborough)', 'on_site', '2026-08-10', '2026-08-10', 6.00,
    'unpaid', NULL, 'Volunteer role.', 8,
    '2026-08-01 23:59:59', 'One outdoor afternoon shift.',
    'Sun protection and water provided; grill area is staff only.',
    'Accessible park with paved paths.',
    'closed', '2026-07-01 14:00:00', '2026-07-01 13:00:00'),
(12, 3, 2, 'Event photographer for community fun run',
    'Photograph the start, finish and award ceremony of a 5 km community run.',
    'Own camera; portfolio link.',
    'Edworthy Park, Calgary', 'on_site', '2026-11-15', '2026-11-15', 5.00,
    'stipend', 100.00, 'Stipend paid after photos are delivered.', 2,
    '2026-11-08 23:59:59', 'One morning outdoors.',
    'Stay off the running course; marshals will guide you.',
    'Finish-line area is step-free.',
    'open', '2026-10-09 16:00:00', '2026-10-09 15:00:00'),
(13, 3, 2, 'New Year''s Eve family event greeters',
    'Welcome families, hand out wristbands and answer questions at the NYE family event.',
    'Friendly and comfortable speaking with the public.',
    'Calgary (Downtown)', 'on_site', '2026-12-31', '2026-12-31', 6.00,
    'unpaid', NULL, 'Volunteer role; snacks provided.', 12,
    '2026-12-20 23:59:59', 'Evening shift 17:00-23:00, indoors.',
    'Crowd management briefing before the shift; staff security on site.',
    'Indoor venue with elevators and accessible washrooms.',
    'open', '2026-10-15 17:00:00', '2026-10-15 16:00:00'),
(14, 1, 1, 'Point-of-sale menu photo shoot',
    'Photograph our menu items for the new point-of-sale screens.',
    NULL,
    'Calgary (Kensington)', 'on_site', NULL, NULL, 6.00,
    'paid', NULL, NULL, 1,
    NULL, NULL, NULL, NULL,
    'draft', NULL, '2026-10-13 15:00:00'),
(15, 3, 2, 'Volunteer coordinator for spring market',
    'Coordinate a team of 10 volunteers for the spring neighbourhood market.',
    'Previous volunteer or team-lead experience.',
    'Calgary (Bridgeland)', 'on_site', '2027-03-15', '2027-04-15', 20.00,
    'stipend', 200.00, 'Stipend paid after the market.', 1,
    '2027-02-28 23:59:59', 'Weekly planning call plus the market day.',
    'Site safety briefing on market day; first-aid kit on site.',
    'Community hall is step-free; calls can be joined by phone.',
    'draft', NULL, '2026-10-15 18:00:00');

INSERT INTO opportunity_skill (opportunity_id, skill_id) VALUES
    (1, 1), (1, 2),
    (2, 2), (2, 3), (2, 10),
    (3, 4), (3, 5), (3, 11),
    (4, 7), (4, 9),
    (5, 9), (5, 10),
    (6, 1), (6, 2), (6, 3),
    (7, 12),
    (8, 7), (8, 8),
    (9, 5), (9, 6),
    (10, 10),
    (11, 7), (11, 9),
    (12, 11),
    (13, 7), (13, 8),
    (14, 11),
    (15, 7), (15, 8);
