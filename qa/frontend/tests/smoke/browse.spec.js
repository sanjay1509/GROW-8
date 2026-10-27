import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openFixture,baseItems,cards,countLabel} from '../../helpers/ui-fixtures.js';
// Built-in screenshot attachment for passed and failed tests.
test.use({ screenshot: 'on' });

test('BRW-001 @smoke Browse page renders toolbar filters and results',async({page})=>{
  await openFixture(page);
  await expect(page.getByRole('heading',{name:'Browse Opportunities'})).toBeVisible();
  await expect(page.getByRole('searchbox',{name:'Search opportunities'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Filters'})).toBeVisible();
  await expect(page.getByRole('combobox',{name:'Sort opportunities'})).toBeVisible();
  await expect(countLabel(page)).toHaveText(String(baseItems.length));
});
test('BRW-002 @smoke Browse cards render API-shaped fixture',async({page})=>{
  await openFixture(page);
  await expect(cards(page)).toHaveCount(baseItems.length);
  await expect(page.getByRole('heading',{name:'Data Entry Support'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Community Garden Cleanup'})).toBeVisible();
});
