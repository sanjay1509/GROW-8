import { test, expect } from '@playwright/test';
import { withDatabase } from '../../helpers/db.js';

test('SAN-DB-01 @sanity seeded opportunity records exist', async () => {
  await withDatabase(async db => {
    const [rows] = await db.query('SELECT COUNT(*) AS total FROM opportunity');
    expect(Number(rows[0].total)).toBeGreaterThan(0);
  });
});

test('SAN-DB-02 @sanity open opportunities have nonempty titles and IDs', async () => {
  await withDatabase(async db => {
    const [rows] = await db.query(`
      SELECT opportunity_id, title, status
      FROM opportunity WHERE status = 'open' LIMIT 20
    `);
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      expect(Number(row.opportunity_id)).toBeGreaterThan(0);
      expect(row.title.trim().length).toBeGreaterThan(0);
      expect(row.status).toBe('open');
    }
  });
});
