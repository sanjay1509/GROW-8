import { test, expect } from '../../helpers/screenshot-every-test.js';
// Built-in screenshot attachment for passed and failed tests.
test.use({ screenshot: 'on' });

// Retains the requested original navigation-only automated case.
test('SMK-FE-01 @smoke homepage loads and Browse navigation works', async ({page}) => {
  await page.goto('/');
  await expect(page.getByRole('link', {name:/Grow8/i})).toBeVisible();
  await page.getByRole('link',{name:'Opportunities',exact:true}).click();
  await expect(page).toHaveURL(/\/opportunities\/?$/);
  await expect(page.getByRole('heading',{name:'Browse Opportunities'})).toBeVisible();
});
