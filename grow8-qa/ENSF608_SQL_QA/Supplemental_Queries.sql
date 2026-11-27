-- ENSF 608 | GROW8 | Independent rubric coverage additions
-- Run on the freshly seeded test database or after the team workflow ROLLBACK.
-- All queries are read-only. The team operations file remains unchanged.

-- [S-1] Basic SELECT / WHERE: Retrieve open remote opportunities.
SELECT opportunity_id, title FROM opportunity WHERE status = 'open' AND work_mode = 'remote' ORDER BY opportunity_id;

-- [S-2] Basic SELECT / WHERE: Retrieve applications waiting for a decision.
SELECT application_id, status FROM application WHERE status = 'pending' ORDER BY application_id;

-- [S-3] Basic SELECT / LIKE: Retrieve contributor profiles associated with a university.
SELECT user_id, institution FROM contributor_profile WHERE institution LIKE '%University%' ORDER BY user_id;

-- [S-4] Basic SELECT / IN: Retrieve selected skills relevant to digital and customer-facing work.
SELECT skill_id, code FROM skill WHERE code IN ('spreadsheets','data-cleaning','customer-service') ORDER BY skill_id;

-- [S-5] GROUP BY / HAVING: Identify opportunities with at least two active applications.
SELECT opportunity_id, COUNT(*) AS active_applications FROM application WHERE status IN ('pending','accepted') GROUP BY opportunity_id HAVING COUNT(*) >= 2 ORDER BY opportunity_id;
