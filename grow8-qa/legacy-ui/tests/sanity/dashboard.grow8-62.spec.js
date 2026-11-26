import {test,expect} from '../../helpers/screenshot-every-test.js';
import {mineItems,mockApi,jsonReply,auth,openDashboard} from '../../helpers/fixtures-62.js';

test('UI-075 DASH-003 @sanity Create Opportunity CTA opens form',async({page})=>{
 await openDashboard(page);
 await page.getByRole('link',{name:'Create Opportunity'}).click();
 await expect(page).toHaveURL(/\/creator\/opportunities\/create$/);
 await expect(page.getByRole('heading',{name:'Create an Opportunity'})).toBeVisible();
});
test('UI-076 DASH-004 @sanity Recent Applications shows four rows, fields and View',async({page})=>{
 await openDashboard(page);
 const table=page.getByRole('table',{name:'Recent applications'});
 await expect(table.locator('tbody tr')).toHaveCount(4);
 for(const title of ['Applicant','Opportunity','Status','Applied Date','Actions'])await expect(table.getByRole('columnheader',{name:title})).toBeVisible();
 await expect(table.locator('tbody')).toContainText('QA Applicant One');
 await expect(table.locator('tbody')).toContainText('Inventory Audit');
 await expect(table.locator('tbody')).toContainText(new Date('2026-10-10T12:00:00Z').toLocaleDateString('en-CA',{year:'numeric',month:'short',day:'numeric'}));
 await expect(table.getByRole('link',{name:/View .* application/})).toHaveCount(4);
});
test('UI-078 DASH-006 @sanity First three opportunities have title, status and application counts',async({page})=>{
 await openDashboard(page);
 const cards=page.locator('.creator-opportunity-card');await expect(cards).toHaveCount(3);
 for(const [title,count,status] of [['Inventory Audit','3 Applications','Open'],['Garden Volunteer','0 Applications','Draft'],['Event Support','1 Applications','Completed']]){
  const card=cards.filter({hasText:title});
  await expect(card).toContainText(count);
  await expect(card).toContainText(status);
 }
});
test('UI-079 DASH-007 @sanity My Opportunities View All navigates to listing',async({page})=>{
 await openDashboard(page);
 await page.locator('.creator-section').filter({has:page.getByRole('heading',{name:'My Opportunities'})}).getByRole('link',{name:/View All/}).click();
 await expect(page).toHaveURL(/\/creator\/opportunities$/);
 await expect(page.getByRole('heading',{name:'My Opportunities'})).toBeVisible();
});
