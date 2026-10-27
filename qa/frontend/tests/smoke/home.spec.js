import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openHome,openFixture} from '../../helpers/ui-fixtures.js';
// Built-in screenshot attachment for passed and failed tests.
test.use({ screenshot: 'on' });

test('HOME-001 @smoke landing page shows primary content',async({page})=>{
  await openHome(page);
  await expect(page.getByRole('link',{name:/Grow8/i}).first()).toBeVisible();
  await expect(page.getByRole('heading',{level:1})).toContainText('Earn Experience.');
  await expect(page.getByRole('heading',{name:'For Contributors'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'For Creators'})).toBeVisible();
});
test('HOME-002 @smoke Grow8 brand returns from Browse to Home',async({page})=>{
  await openFixture(page);
  await page.locator('.grow8-brand').click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading',{level:1})).toContainText('Build Skills.');
});
