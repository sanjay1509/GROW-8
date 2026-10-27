import { test, expect } from '@playwright/test';
import { withDatabase } from '../../helpers/db.js';

test('REG-DB-01 @regression opportunity foreign keys point to valid organizations', async () => {
  await withDatabase(async db => {
    const [rows] = await db.query(`
      SELECT COUNT(*) AS broken_links
      FROM opportunity o
      LEFT JOIN creator_organization c ON c.organization_id = o.organization_id
      WHERE c.organization_id IS NULL
    `);
    expect(Number(rows[0].broken_links)).toBe(0);
  });
});

test('REG-DB-02 @regression open opportunities have mandatory safety disclosures', async () => {
  await withDatabase(async db => {
    const [rows] = await db.query(`
      SELECT COUNT(*) AS invalid_opportunities FROM opportunity
      WHERE status = 'open' AND (
        safety_information IS NULL OR working_conditions IS NULL OR
        accessibility_details IS NULL OR expected_hours IS NULL OR
        application_deadline IS NULL OR published_at IS NULL
      )
    `);
    expect(Number(rows[0].invalid_opportunities)).toBe(0);
  });
});

test('REG-DB-03 @regression database defines hours and date CHECK constraints', async () => {
  await withDatabase(async db => {
    const [rows] = await db.execute(`
      SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'opportunity'
        AND CONSTRAINT_TYPE = 'CHECK'
    `);
    const names = new Set(rows.map(row => row.CONSTRAINT_NAME));
    expect(names.has('chk_opportunity_expected_hours')).toBe(true);
    expect(names.has('chk_opportunity_dates')).toBe(true);
  });
});
