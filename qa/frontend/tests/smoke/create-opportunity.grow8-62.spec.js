import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openCreate,fillValid,categories,auth,mockApi,jsonReply} from '../../helpers/fixtures-62.js';

test('CRT-001 @smoke Create form shows all four sections and action buttons',async({page})=>{
 await openCreate(page);
 for(const name of ['Basic information','Work arrangement','Compensation','Safety and accessibility'])await expect(page.getByRole('heading',{name})).toBeVisible();
 for(const name of ['Save Draft','Publish Opportunity'])await expect(page.getByRole('button',{name})).toBeVisible();
 await expect(page.getByRole('link',{name:'Cancel'})).toBeVisible();
});
test('CRT-002 @smoke Categories dropdown uses API categories',async({page})=>{
 await openCreate(page);
 const combo=page.locator('#category_id');
 await expect(combo.locator('option')).toHaveCount(categories.length+1);
 await expect(combo.getByRole('option',{name:'Knowledge-based'})).toHaveCount(1);
 await expect(combo.getByRole('option',{name:'Community'})).toHaveCount(1);
});
test('CRT-009 @smoke Save Draft creates authenticated draft, never publishes',async({page})=>{
 let created=0;let published=0;let payload;
 await openCreate(page,{onCreate:(route,request)=>{
   created++;payload=request.postDataJSON();expect(request.headers()['authorization']).toBe('Bearer grow8-e2e-test-token');
   return jsonReply(route,201,{opportunity_id:601,status:'draft'});
 },onPublish:(route)=>{published++;return jsonReply(route,200,{status:'open'})}});
 await fillValid(page);
 await page.getByRole('button',{name:'Save Draft'}).click();
 await expect(page.getByRole('status')).toContainText('Your opportunity draft was saved.');
 expect(created).toBe(1);expect(published).toBe(0);
 expect(payload.title).toBe('Community Digital Training');
 expect(payload.category).toBe('knowledge');
 await expect(page).toHaveURL(/\/creator\/opportunities$/,{timeout:5000});
});
