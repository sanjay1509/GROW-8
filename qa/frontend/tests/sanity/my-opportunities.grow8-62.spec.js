import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openMine} from '../../helpers/fixtures-62.js';

test('MYOP-003 @sanity Title and description search update cards and count',async({page})=>{
 await openMine(page);
 const search=page.getByRole('textbox',{name:'Search opportunities'});
 await search.fill('Inventory Audit');
 await expect(page.locator('.mo-card')).toHaveCount(1);
 await expect(page.locator('.mo-card').first()).toContainText('Inventory Audit');
 await expect(page.locator('.mo-result-count')).toContainText('Showing 1 of 3');
 await search.fill('community garden');
 await expect(page.locator('.mo-card')).toHaveCount(1);
 await expect(page.locator('.mo-card').first()).toContainText('Garden Volunteer');
});
test('MYOP-004 @sanity Status filter intersects search',async({page})=>{
 await openMine(page);
 await page.getByRole('combobox',{name:'Filter by status'}).selectOption('draft');
 await expect(page.locator('.mo-card')).toHaveCount(1);
 await page.getByRole('textbox',{name:'Search opportunities'}).fill('Garden');
 await expect(page.locator('.mo-card')).toHaveCount(1);
 await expect(page.locator('.mo-card').first()).toContainText('Garden Volunteer');
 await page.getByRole('textbox',{name:'Search opportunities'}).fill('Inventory');
 await expect(page.getByRole('heading',{name:'No matching opportunities'})).toBeVisible();
});
