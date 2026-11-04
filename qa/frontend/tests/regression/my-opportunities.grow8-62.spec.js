import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openMine,mineItems,auth,mockApi,jsonReply} from '../../helpers/fixtures-62.js';

test('MYOP-005 @regression Refresh refetches and displays changed records',async({page})=>{
 let count=0;
 await auth(page);
 await mockApi(page,(route,path)=>{
  if(path.endsWith('/opportunities/mine')){count++;return jsonReply(route,200,{items:count===1?mineItems:[...mineItems,{...mineItems[0],opportunity_id:399,title:'Newly Added Opportunity'}]});}
  return jsonReply(route,404,{});
 });
 await page.goto('/creator/opportunities');
 await expect(page.locator('.mo-card')).toHaveCount(3);
 await page.getByRole('button',{name:'Refresh'}).click();
 await expect(page.locator('.mo-card')).toHaveCount(4);
 await expect(page.getByRole('heading',{name:'Newly Added Opportunity'})).toBeVisible();
 expect(count).toBeGreaterThanOrEqual(2);
});
test('MYOP-006 @regression No matching records displays helpful empty state',async({page})=>{
 await openMine(page);
 await page.getByRole('textbox',{name:'Search opportunities'}).fill('not-in-results-ever-123');
 await expect(page.getByRole('heading',{name:'No matching opportunities'})).toBeVisible();
 await expect(page.getByText('Try another search term or status filter.')).toBeVisible();
});
test('MYOP-007 @regression No opportunities shows empty state and create CTA',async({page})=>{
 await openMine(page,{items:[]});
 await expect(page.getByRole('heading',{name:'No opportunities yet'})).toBeVisible();
 await expect(page.getByRole('link',{name:'Create your first opportunity'})).toBeVisible();
});
test('MYOP-008 @regression Missing token shows sign-in requirement without protected fetch',async({page})=>{
 let requests=0;
 await mockApi(page,(route,path)=>{if(path.endsWith('/opportunities/mine'))requests++;return jsonReply(route,200,{items:mineItems})});
 await page.goto('/creator/opportunities');
 await expect(page.getByRole('alert')).toContainText('Unable to load opportunities');
 await expect(page.getByRole('alert')).toContainText('Please sign in as a creator');
 expect(requests).toBe(0);
});
test('MYOP-009 @regression Failed API then Try again recovers records',async({page})=>{
 let requests=0;await auth(page);
 await mockApi(page,(route,path)=>{
  if(path.endsWith('/opportunities/mine')){requests++;return requests===1?jsonReply(route,503,{detail:'Unavailable'}):jsonReply(route,200,{items:mineItems})}
  return jsonReply(route,404,{});
 });
 await page.goto('/creator/opportunities');
 await expect(page.getByRole('alert')).toContainText('HTTP 503');
 await page.getByRole('button',{name:'Try again'}).click();
 await expect(page.locator('.mo-card')).toHaveCount(3);
 expect(requests).toBeGreaterThanOrEqual(2);
});
test('MYOP-010 @regression Create and View navigate to functional destinations',async({page})=>{
 await openMine(page);
 await page.getByRole('link',{name:'Create Opportunity'}).click();
 await expect(page).toHaveURL(/\/creator\/opportunities\/create$/);
 await page.goto('/creator/opportunities');
 await expect(page.locator('.mo-card')).toHaveCount(3);
 await page.locator('.mo-card').filter({hasText:'Inventory Audit'}).getByRole('link',{name:'View'}).click();
 await expect(page).toHaveURL(/\/creator\/opportunities\/301$/);
 await expect(page.getByRole('heading',{name:'Inventory Audit'})).toBeVisible();
});
