import {test,expect} from '../../helpers/screenshot-every-test.js';

test('DASH-001 @smoke Creator Dashboard loads welcome and sections',async({page})=>{
 await page.goto('/creator/dashboard');
 await expect(page).toHaveURL(/\/creator\/dashboard$/);
 await expect(page.getByRole('heading',{name:/Welcome, Tech for Good/})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Recent Applications'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'My Opportunities'})).toBeVisible();
});
test('DASH-002 @smoke Summary cards show configured counts',async({page})=>{
 await page.goto('/creator/dashboard');
 const card=page.locator('.creator-stat-card');
 await expect(card).toHaveCount(4);
 for(const [label,value] of [['Total Opportunities','5'],['Total Applications','12'],['In Progress','3'],['Completed','8']]){
  const item=card.filter({hasText:label});
  await expect(item.locator('.creator-stat-label')).toHaveText(label);
  await expect(item.locator('.creator-stat-value')).toHaveText(value);
 }
});
