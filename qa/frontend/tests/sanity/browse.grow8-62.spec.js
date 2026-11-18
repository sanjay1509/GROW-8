import {test,expect} from '../../helpers/screenshot-every-test.js';
import {browse,visibleBrowseCards,browseSearch,browseCount,baseItems} from '../../helpers/fixtures-62.js';
test('BRW-003 @sanity Search by title filters and updates count',async({page})=>{
 await browse(page);await browseSearch(page).fill('Inventory Spreadsheet');
 await expect(visibleBrowseCards(page)).toHaveCount(1);
 await expect(visibleBrowseCards(page).first()).toContainText('Inventory Spreadsheet Cleanup');
 await expect(browseCount(page)).toHaveText('1');
});
test('BRW-006 @sanity Filter by category displays matching opportunities',async({page})=>{
 await browse(page);
 await page.getByRole('group',{name:'Category'}).getByLabel('Community').check();
 await expect(visibleBrowseCards(page)).toHaveCount(3);
 await expect(visibleBrowseCards(page)).toContainText(['Community Garden Cleanup','On-site Photography','Hybrid Event Planning']);
});
test('BRW-011 @sanity Clear all resets search and filters',async({page})=>{
 await browse(page);
 await browseSearch(page).fill('Garden');
 await page.getByRole('group',{name:'Category'}).getByLabel('Community').check();
 await expect(visibleBrowseCards(page)).toHaveCount(1);
 await page.getByRole('button',{name:'Clear all'}).click();
 await expect(browseSearch(page)).toHaveValue('');
 await expect(page.getByRole('group',{name:'Category'}).getByLabel('Community')).not.toBeChecked();
 await expect(visibleBrowseCards(page)).toHaveCount(baseItems.length);
});
test('BRW-016 @sanity Modal close button and icon each dismiss dialog',async({page})=>{
 await browse(page);const first=visibleBrowseCards(page).first().getByRole('button',{name:'View Details'});
 await first.click();await page.getByRole('dialog').locator('.browse-modal-done').click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await first.click();await page.getByRole('dialog').locator('.browse-modal-close').click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await expect(page).toHaveURL(/\/opportunities$/);
});
