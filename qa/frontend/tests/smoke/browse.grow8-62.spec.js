import {test,expect} from '../../helpers/screenshot-every-test.js';
import {browse,baseItems,visibleBrowseCards,browseCount} from '../../helpers/fixtures-62.js';

test('BRW-001 @smoke Browse renders heading, search, filters, sort and cards',async({page})=>{
 await browse(page);
 await expect(page.getByRole('heading',{name:'Browse Opportunities'})).toBeVisible();
 await expect(page.getByRole('searchbox',{name:'Search opportunities'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Filters'})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Sort opportunities'})).toBeVisible();
 await expect(browseCount(page)).toHaveText(String(baseItems.length));
});
test('BRW-002 @smoke Cards display API title, organization, location, mode, hours, category, deadline',async({page})=>{
 await browse(page);
 const item=baseItems[0];
 const card=visibleBrowseCards(page).filter({has:page.getByRole('heading',{name:item.title})});
 await expect(card).toContainText(item.title);
 await expect(card).toContainText(item.organization.name);
 await expect(card).toContainText(item.location);
 await expect(card).toContainText('Remote');
 await expect(card).toContainText(`${item.expected_hours} hrs`);
 await expect(card).toContainText(item.category.name);
 await expect(card).toContainText('Deadline:');
 await expect(card).toContainText('2030');
});
test('BRW-015 @smoke View Details displays correct opportunity details',async({page})=>{
 await browse(page);
 await visibleBrowseCards(page).filter({hasText:'Data Entry Support'}).getByRole('button',{name:'View Details'}).click();
 const dlg=page.getByRole('dialog');
 await expect(dlg).toBeVisible();
 for(const value of ['Data Entry Support','Maple Street Bakery','Organize community spreadsheets.','Calgary','Remote','8 hrs','Spreadsheets']){
  await expect(dlg).toContainText(value);
 }
 await expect(dlg).toContainText('Deadline');
});
