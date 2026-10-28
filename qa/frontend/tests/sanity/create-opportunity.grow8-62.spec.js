import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openCreate,fillValid,jsonReply} from '../../helpers/fixtures-62.js';

test('CRT-003 @sanity Required title, category, description block submission',async({page})=>{
 let posts=0;await openCreate(page,{onCreate:(route)=>{posts++;return jsonReply(route,201,{opportunity_id:601})}});
 const save=page.getByRole('button',{name:'Save Draft'});
 await save.click();expect(await page.locator('#title').evaluate(el=>el.validity.valueMissing)).toBe(true);
 await page.locator('#title').fill('Valid title');await save.click();
 expect(await page.locator('#category_id').evaluate(el=>el.validity.valueMissing)).toBe(true);
 await page.locator('#category_id').selectOption('knowledge');await save.click();
 expect(await page.locator('#description').evaluate(el=>el.validity.valueMissing)).toBe(true);
 expect(posts).toBe(0);
});
test('CRT-004 @sanity All valid form data can be entered and retained',async({page})=>{
 await openCreate(page);await fillValid(page);
 for(const [field,value] of [['title','Community Digital Training'],['category_id','knowledge'],['description','Teach introductory digital literacy and support local volunteers.'],['location','Calgary'],['start_date','2030-10-20'],['end_date','2030-10-22'],['application_deadline','2030-10-18'],['expected_hours','8'],['applicant_limit','10']]){
  await expect(page.locator('#'+field)).toHaveValue(value);
 }
});
test('CRT-007 @sanity Paid displays required amount/currency and blocks invalid amount',async({page})=>{
 await openCreate(page);
 await page.locator('#compensation_type').selectOption('paid');
 await expect(page.locator('#compensation_amount')).toBeVisible();
 await expect(page.locator('#compensation_currency')).toBeVisible();
 await expect(page.locator('#compensation_currency').getByRole('option',{name:/CAD/})).toHaveCount(1);
 await expect(page.locator('#compensation_currency').getByRole('option',{name:/USD/})).toHaveCount(1);
 expect(await page.locator('#compensation_amount').evaluate(el=>el.required)).toBe(true);
 await page.locator('#compensation_amount').fill('-5');
 expect(await page.locator('#compensation_amount').evaluate(el=>el.validity.rangeUnderflow)).toBe(true);
 await page.locator('#compensation_amount').fill('25');
 await expect(page.locator('#compensation_amount')).toHaveValue('25');
});
test('CRT-010 @sanity Publishing creates then publishes returned ID, shows success',async({page})=>{
 const steps=[];
 await openCreate(page,{onCreate:(route,request)=>{steps.push(['create',request.postDataJSON()]);return jsonReply(route,201,{opportunity_id:731,status:'draft'})},onPublish:(route,request)=>{steps.push(['publish',new URL(request.url()).pathname]);return jsonReply(route,200,{opportunity_id:731,status:'open'})}});
 await fillValid(page);
 await page.getByRole('button',{name:'Publish Opportunity'}).click();
 await expect(page.getByRole('status')).toContainText('published successfully');
 expect(steps.map(x=>x[0])).toEqual(['create','publish']);
 expect(steps[1][1]).toBe('/api/v1/opportunities/731/publish');
 await expect(page).toHaveURL(/\/creator\/opportunities$/,{timeout:5000});
});
