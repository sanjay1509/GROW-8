import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openHome,openFixture} from '../../helpers/ui-fixtures.js';
// Built-in screenshot attachment for passed and failed tests.
test.use({ screenshot: 'on' });

test('HOME-004 @sanity Home navbar returns from Browse',async({page})=>{
  await openFixture(page);
  await page.getByRole('link',{name:'Home',exact:true}).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading',{level:1})).toBeVisible();
});
test('HOME-005 @sanity Explore Opportunities CTA navigates to Browse',async({page})=>{
  await openHome(page);
  await page.getByRole('link',{name:'Explore Opportunities'}).click();
  await expect(page.getByRole('heading',{name:'Browse Opportunities'})).toBeVisible();
});
test('HOME-006 @sanity featured View All navigates to Browse',async({page})=>{
  await openHome(page);
  await page.getByRole('link',{name:'View All'}).click();
  await expect(page).toHaveURL(/\/opportunities\/?$/);
});
test('HOME-007 @sanity hero text and descriptive image render',async({page})=>{
  await openHome(page);
  await expect(page.getByRole('heading',{level:1})).toContainText('Support Communities.');
  const hero=page.getByRole('img',{name:'Students collaborating around a laptop'});
  await expect(hero).toBeVisible();
  expect(await hero.evaluate(img=>img.complete && img.naturalWidth>0)).toBe(true);
});
test('HOME-008 @sanity Contributor card is keyboard-focusable',async({page})=>{
  await openHome(page);
  const button=page.getByRole('button',{name:'Open Contributor Dashboard'});
  await expect(button).toBeVisible();
  await button.focus();
  await expect(button).toBeFocused();
});
test('HOME-009 @sanity Creator card is keyboard-focusable',async({page})=>{
  await openHome(page);
  const button=page.getByRole('button',{name:'Open Creator Dashboard'});
  await expect(button).toBeVisible();
  await button.focus();
  await expect(button).toBeFocused();
});
