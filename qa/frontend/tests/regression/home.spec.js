import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openHome} from '../../helpers/ui-fixtures.js';
const featuredTitles=['Social Media Support','Event Volunteer Support','Data Entry and Organization'];
const featured=page=>page.locator('.grow8-featured');
// Built-in screenshot attachment for passed and failed tests.
test.use({ screenshot: 'on' });

test('HOME-010 @regression exactly three featured sample cards include metadata',async({page})=>{
  await openHome(page);
  const cards=featured(page).locator('.grow8-opportunity-card');
  await expect(cards).toHaveCount(3);
  for(const title of featuredTitles) await expect(featured(page).getByRole('heading',{name:title})).toBeVisible();
  for(const card of await cards.all()) {
    await expect(card.locator('.grow8-organization')).not.toBeEmpty();
    await expect(card.locator('.grow8-opportunity-meta')).not.toBeEmpty();
    await expect(card.locator('.grow8-opportunity-tags')).not.toBeEmpty();
  }
});
test('HOME-011 @regression reloading preserves sample featured cards regardless of order',async({page})=>{
  await openHome(page);
  for(let i=0;i<3;i++){
    if(i) await page.reload();
    const values=await featured(page).locator('.grow8-opportunity-card h3').allTextContents();
    expect(values.sort()).toEqual([...featuredTitles].sort());
  }
});
test('HOME-012 @regression featured opportunity cards are informational',async({page})=>{
  await openHome(page);
  const card=featured(page).locator('.grow8-opportunity-card').first();
  await card.click();
  await expect(page).toHaveURL(/\/$/);
});
test('HOME-013 @regression role controls navigate to configured dashboard paths',async({page})=>{
  await openHome(page);
  await page.getByRole('button',{name:'Open Contributor Dashboard'}).click();
  await expect(page).toHaveURL(/\/contributor-dashboard\/?$/);
  await page.goto('/');
  await page.getByRole('button',{name:'Open Creator Dashboard'}).click();
  await expect(page).toHaveURL(/\/creator-dashboard\/?$/);
  // Dashboard pages are placeholders; do not claim their content is working.
});
test('HOME-014 @regression About section shows purpose and three benefits',async({page})=>{
  await openHome(page);
  const about=page.locator('.grow8-about');
  await about.scrollIntoViewIfNeeded();
  await expect(about.getByRole('heading',{name:/About Grow8/})).toBeVisible();
  for(const item of ['Gain practical experience','Develop real-world skills','Make a positive community impact']) await expect(about.getByText(item)).toBeVisible();
});
test('HOME-015 @regression Mission Purpose Vision cards show descriptions',async({page})=>{
  await openHome(page);
  for(const title of ['Our Mission','Our Purpose','Our Vision']){
    const card=page.locator('.grow8-about-value-card').filter({has:page.getByRole('heading',{name:title,exact:true})});
    await card.scrollIntoViewIfNeeded();
    await expect(card).toBeVisible();
    await expect(card.locator('p')).not.toBeEmpty();
  }
});
test('HOME-016 @regression Back to top appears after scrolling',async({page})=>{
  await openHome(page);await page.evaluate(()=>window.scrollTo(0,700));
  await expect(page.getByRole('button',{name:'Back to top'})).toHaveClass(/visible/);
});
test('HOME-017 @regression Back to top returns viewport to start',async({page})=>{
  await openHome(page);await page.evaluate(()=>window.scrollTo(0,1200));
  await page.getByRole('button',{name:'Back to top'}).click();
  await expect.poll(async()=>page.evaluate(()=>window.scrollY)).toBeLessThan(30);
});
test('HOME-018 @regression reduced-motion homepage still displays content',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await openHome(page);
  await expect(page.getByRole('heading',{level:1})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Our Mission'})).toBeVisible();
});
test('HOME-019 @regression mobile homepage accessible without overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844});await openHome(page);
  await expect(page.getByRole('link',{name:'Explore Opportunities'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+2)).toBe(true);
});
test('HOME-020 @regression tablet homepage retains readable controls',async({page})=>{
  await page.setViewportSize({width:768,height:1024});await openHome(page);
  await expect(page.getByRole('link',{name:'Get Started'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+2)).toBe(true);
});
test('HOME-021 @regression keyboard can activate primary Home navigation',async({page})=>{
  await openHome(page);
  const link=page.getByRole('link',{name:'Explore Opportunities'});
  await link.focus();await expect(link).toBeFocused();await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/opportunities\/?$/);
});
test('HOME-022 @regression hero image has meaningful alt text',async({page})=>{
  await openHome(page);
  await expect(page.getByRole('img',{name:'Students collaborating around a laptop'})).toHaveAttribute('alt','Students collaborating around a laptop');
});
