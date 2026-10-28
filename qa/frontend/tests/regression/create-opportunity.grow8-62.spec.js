import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openCreate,fillValid,jsonReply,mockApi,categories,auth} from '../../helpers/fixtures-62.js';

test('CRT-005 @regression Invalid date sequences block submit',async({page})=>{
 let posts=0;await openCreate(page,{onCreate:route=>{posts++;return jsonReply(route,201,{opportunity_id:601})}});
 await fillValid(page);
 await page.locator('#end_date').fill('2030-10-18');
 await page.getByRole('button',{name:'Save Draft'}).click();
 const invalidEnd=await page.locator('#end_date').evaluate(el=>!el.validity.valid);
 const customError=await page.getByRole('alert').count();
 expect(invalidEnd||customError>0).toBe(true);
 await page.locator('#end_date').fill('2030-10-22');
 await page.locator('#application_deadline').fill('2030-10-21');
 await page.getByRole('button',{name:'Save Draft'}).click();
 await expect(page.getByRole('alert')).toContainText('application deadline should not be after the start date');
 expect(posts).toBe(0);
});
test('CRT-006 @regression Invalid hours and applicant-limit numeric constraints',async({page})=>{
 await openCreate(page);
 for(const field of ['expected_hours','applicant_limit']){
  const input=page.locator('#'+field);
  for(const value of ['0','-2','1.5']){
   await input.fill(value);
   const valid=await input.evaluate(el=>el.validity.valid);
   expect(valid,`${field}=${value} must not be valid`).toBe(false);
  }
 }
});
test('CRT-008 @regression Switching Paid to Unpaid clears paid-only payload amount',async({page})=>{
 let body;
 await openCreate(page,{onCreate:(route,request)=>{body=request.postDataJSON();return jsonReply(route,201,{opportunity_id:601})}});
 await fillValid(page);
 await page.locator('#compensation_type').selectOption('paid');
 await page.locator('#compensation_amount').fill('125');
 await page.locator('#compensation_currency').selectOption('USD');
 await page.locator('#compensation_type').selectOption('unpaid');
 await expect(page.locator('#compensation_amount')).toHaveCount(0);
 await expect(page.locator('#compensation_currency')).toHaveCount(0);
 await page.getByRole('button',{name:'Save Draft'}).click();
 await expect(page.getByRole('status')).toBeVisible();
 expect(body.compensation_type).toBe('unpaid');
 expect(body.compensation_amount??null).toBeNull();
});
test('CRT-011 @regression Missing token blocks create and shows sign-in notice',async({page})=>{
 let posts=0;
 await openCreate(page,{token:false,onCreate:route=>{posts++;return jsonReply(route,201,{opportunity_id:601})}});
 await fillValid(page);await page.getByRole('button',{name:'Save Draft'}).click();
 await expect(page.getByRole('alert')).toContainText('Please sign in as a creator');
 expect(posts).toBe(0);
});
test('CRT-012 @regression Backend create validation failure stays on form',async({page})=>{
 await openCreate(page,{onCreate:route=>jsonReply(route,422,{detail:[{msg:'Expected hours must be positive'}]})});
 await fillValid(page);await page.getByRole('button',{name:'Save Draft'}).click();
 await expect(page.getByRole('alert')).toContainText('Expected hours must be positive');
 await expect(page).toHaveURL(/\/creator\/opportunities\/create$/);
 await expect(page.getByRole('status')).toHaveCount(0);
});
test('CRT-013 @regression Publish failure after create shows partial-success error',async({page})=>{
 let creates=0,publishes=0;
 await openCreate(page,{onCreate:route=>{creates++;return jsonReply(route,201,{opportunity_id:731,status:'draft'})},onPublish:route=>{publishes++;return jsonReply(route,409,{detail:'Publication validation failed'})}});
 await fillValid(page);await page.getByRole('button',{name:'Publish Opportunity'}).click();
 await expect(page.getByRole('alert')).toContainText('created, but publishing failed');
 await expect(page.getByRole('alert')).toContainText('Publication validation failed');
 await expect(page.getByRole('status')).toHaveCount(0);
 expect(creates).toBe(1);expect(publishes).toBe(1);
 await expect(page).toHaveURL(/\/creator\/opportunities\/create$/);
});
test('CRT-014 @regression Failed and empty categories prevent selection and submission',async({page})=>{
 let posts=0,kind='error';await auth(page);
 await mockApi(page,(route,path,request)=>{
  if(path.endsWith('/categories'))return kind==='error'?jsonReply(route,503,{detail:'Unavailable'}):jsonReply(route,200,{items:[]});
  if(path.endsWith('/opportunities')&&request.method()==='POST'){posts++;return jsonReply(route,201,{opportunity_id:601})}
  return jsonReply(route,404,{});
 });
 await page.goto('/creator/opportunities/create');
 await expect(page.getByRole('alert')).toContainText('Unable to load categories from the backend');
 kind='empty';await page.reload();
 await expect(page.getByText('No categories found. Check GET /api/v1/categories.')).toBeVisible();
 await page.locator('#title').fill('Required title');await page.locator('#description').fill('Valid description');
 await page.getByRole('button',{name:'Save Draft'}).click();
 expect(await page.locator('#category_id').evaluate(el=>el.validity.valueMissing)).toBe(true);
 expect(posts).toBe(0);
});
test('CRT-015 @regression Cancel and Back to Dashboard navigate without POST',async({page})=>{
 let posts=0;
 await openCreate(page,{onCreate:route=>{posts++;return jsonReply(route,201,{opportunity_id:601})}});
 await page.locator('#title').fill('Unsaved work');
 await page.getByRole('link',{name:'Cancel'}).click();
 await expect(page).toHaveURL(/\/creator\/dashboard$/);
 await page.goto('/creator/opportunities/create');
 await page.getByRole('link',{name:'Back to Dashboard'}).click();
 await expect(page).toHaveURL(/\/creator\/dashboard$/);
 expect(posts).toBe(0);
});
