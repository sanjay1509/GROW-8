import { test, expect } from '@playwright/test';
import { withDatabase } from '../../helpers/db.js';

test('SMK-DB-01 @smoke can connect to the MySQL database', async () => {
  await withDatabase(async db => {
    const [rows] = await db.query('SELECT 1 AS connection_ok');
    expect(rows[0].connection_ok).toBe(1);
  });
});

test('SMK-DB-02 @smoke required opportunity table exists', async () => {
  await withDatabase(async db => {
    const [rows] = await db.query('SHOW TABLES LIKE ?', ['opportunity']);
    expect(rows).toHaveLength(1);
  });
});
