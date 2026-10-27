import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openFixture,cards,search,checkbox,dialog,cardFor,baseItems} from '../../helpers/ui-fixtures.js';
// Built-in screenshot attachment for passed and failed tests.
test.use({ screenshot: 'on' });

test('BRW-003 @sanity Browse shows loading status for pending request',async({page})=>{
  let release;
  const wait=new Promise(resolve=>release=resolve);
  await page.route('**/api/v1/opportunities?**',async route=>{await wait;await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:baseItems,total:baseItems.length})});});
  await page.goto('/opportunities');
  await expect(page.getByText('Loading opportunities...')).toBeVisible();
  release();
  await expect(cards(page)).toHaveCount(baseItems.length);
});
test('BRW-004 @sanity title search selects only matching opportunity',async({page})=>{
  await openFixture(page);await search(page).fill('garden');
  await expect(cards(page)).toHaveCount(1);
  await expect(cardFor(page,'Community Garden Cleanup')).toBeVisible();
});
test('BRW-005 @sanity category checkbox restricts cards',async({page})=>{
  await openFixture(page);
  await checkbox(page,'Category','Community').check();
  await expect(cards(page)).toHaveCount(3);
  await expect(cardFor(page,'Data Entry Support')).toHaveCount(0);
});
test('BRW-006 @sanity Reset filters clears selection and restores cards',async({page})=>{
  await openFixture(page);await checkbox(page,'Category','Community').check();
  await page.getByRole('button',{name:'Reset filters'}).click();
  await expect(checkbox(page,'Category','Community')).not.toBeChecked();
  await expect(cards(page)).toHaveCount(baseItems.length);
});
test('BRW-007 @sanity opportunity details dialog opens and closes',async({page})=>{
  await openFixture(page);
  await cardFor(page,'Data Entry Support').getByRole('button',{name:'View Details'}).click();
  await expect(dialog(page)).toBeVisible();
  await expect(dialog(page).getByRole('heading',{name:'Data Entry Support'})).toBeVisible();
  await dialog(page).getByRole('button',{name:'Close Details',exact:true}).click();
  await expect(dialog(page)).toHaveCount(0);
});
