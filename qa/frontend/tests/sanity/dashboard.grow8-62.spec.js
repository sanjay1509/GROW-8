import {test,expect} from '../../helpers/screenshot-every-test.js';
import {mineItems,mockApi,jsonReply,auth} from '../../helpers/fixtures-62.js';

test('DASH-003 @sanity Create Opportunity CTA opens form',async({page})=>{
 await page.goto('/creator/dashboard');
 await page.getByRole('link',{name:'Create Opportunity'}).click();
 await expect(page).toHaveURL(/\/creator\/opportunities\/create$/);
 await expect(page.getByRole('heading',{name:'Create an Opportunity'})).toBeVisible();
});
test('DASH-004 @sanity Recent Applications shows four rows, fields and View',async({page})=>{
 await page.goto('/creator/dashboard');
 const table=page.getByRole('table',{name:'Recent applications'});
 await expect(table.locator('tbody tr')).toHaveCount(4);
 for(const title of ['Applicant','Opportunity','Status','Applied Date','Actions'])await expect(table.getByRole('columnheader',{name:title})).toBeVisible();
 await expect(table.locator('tbody')).toContainText('Sanjay Kumar');
 await expect(table.locator('tbody')).toContainText('Social Media Support');
 await expect(table.locator('tbody')).toContainText('2026-10-10');
 await expect(table.getByRole('link',{name:/View .* application/})).toHaveCount(4);
});
test('DASH-006 @sanity First three opportunities have title, status and application counts',async({page})=>{
 await page.goto('/creator/dashboard');
 const cards=page.locator('.creator-opportunity-card');await expect(cards).toHaveCount(3);
 for(const [title,count,status] of [['Social Media Support','5 Applications','Open'],['Event Volunteer Support','3 Applications','Open'],['Data Entry and Organization','3 Applications','Open']]){
  const card=cards.filter({hasText:title});
  await expect(card).toContainText(count);
  await expect(card).toContainText(status);
 }
});
test('DASH-007 @sanity My Opportunities View All navigates to listing',async({page})=>{
 await auth(page);await mockApi(page,async(route,path)=>path.endsWith('/opportunities/mine')?jsonReply(route,200,{items:mineItems}):jsonReply(route,404,{}));
 await page.goto('/creator/dashboard');
 await page.locator('.creator-section').filter({has:page.getByRole('heading',{name:'My Opportunities'})}).getByRole('link',{name:/View All/}).click();
 await expect(page).toHaveURL(/\/creator\/opportunities$/);
 await expect(page.getByRole('heading',{name:'My Opportunities'})).toBeVisible();
});
