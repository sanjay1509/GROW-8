import {test,expect} from '../../helpers/screenshot-every-test.js';

test('HOME-001 @smoke Home loads and primary sections render',async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('link',{name:/Grow8/}).first()).toBeVisible();
 await expect(page.getByRole('heading',{level:1})).toContainText('Earn Experience.');
 await expect(page.getByRole('heading',{name:'Featured Opportunities'})).toBeVisible();
 await expect(page.getByRole('heading',{name:/About Grow8/})).toBeVisible();
});
test('HOME-002 @smoke Brand logo returns to Home',async({page})=>{
 await page.goto('/opportunities');
 await page.locator('a.grow8-brand').click();
 await expect(page).toHaveURL(/\/$/);
 await expect(page.getByRole('heading',{level:1})).toContainText('Build Skills.');
});
