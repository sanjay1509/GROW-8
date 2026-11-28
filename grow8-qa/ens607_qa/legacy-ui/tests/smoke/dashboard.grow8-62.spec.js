import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openDashboard} from '../../helpers/fixtures-62.js';

test('UI-073 DASH-001 @smoke Creator Dashboard loads welcome and sections',async({page})=>{
 await openDashboard(page);
 await expect(page).toHaveURL(/\/creator\/dashboard$/);
 await expect(page.getByRole('heading',{name:/Welcome, Test Organization/})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Recent Applications'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'My Opportunities'})).toBeVisible();
});
test('UI-074 DASH-002 @smoke Summary cards show configured counts',async({page})=>{
 await openDashboard(page);
 const card=page.locator('.creator-stat-card');
 await expect(card).toHaveCount(4);
 for(const [label,value] of [['Total Opportunities','3'],['Total Applications','4'],['In Progress','1'],['Completed','1']]){
  const item=card.filter({hasText:label});
  await expect(item.locator('.creator-stat-label')).toHaveText(label);
  await expect(item.locator('.creator-stat-value')).toHaveText(value);
 }
});
