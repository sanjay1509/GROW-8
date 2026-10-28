import {test,expect} from '../../helpers/screenshot-every-test.js';
import {browse,baseItems,visibleBrowseCards,browseCount,browseSearch,titleList,mockApi,jsonReply} from '../../helpers/fixtures-62.js';
const category=page=>page.getByRole('group',{name:'Category'});
const mode=page=>page.getByRole('group',{name:'Work mode'});
const hours=page=>page.getByRole('group',{name:'Time commitment'});
const skills=page=>page.getByRole('group',{name:'Skills'});
test('BRW-004 @regression Search organization or skills case-insensitively',async({page})=>{
 await browse(page);
 await browseSearch(page).fill('mApLe sTrEeT');
 await expect(visibleBrowseCards(page)).toHaveCount(1);
 await expect(visibleBrowseCards(page).first()).toContainText('Data Entry Support');
 await browseSearch(page).fill('tRaNsLaTiOn');
 await expect(visibleBrowseCards(page)).toHaveCount(1);
 await expect(visibleBrowseCards(page).first()).toContainText('Remote Content Review');
});
test('BRW-005 @regression Unmatched search presents empty message and clear action',async({page})=>{
 await browse(page);await browseSearch(page).fill('unfindable-opportunity-999');
 await expect(page.getByRole('heading',{name:'No opportunities found'})).toBeVisible();
 await page.getByRole('button',{name:'Clear filters',exact:true}).click();
 await expect(visibleBrowseCards(page)).toHaveCount(baseItems.length);
});
test('BRW-007 @regression Work modes Remote, On-site, Hybrid filter correctly',async({page})=>{
 await browse(page);
 for(const [selection,expectedCount] of [['Remote',2],['On-site',2],['Hybrid',2]]){
  await mode(page).getByLabel(selection,{exact:true}).check();
  await expect(visibleBrowseCards(page)).toHaveCount(expectedCount);
  for(const title of await titleList(page)){
    const item=baseItems.find(x=>x.title===title);
    expect(item.work_mode==='on_site'?'On-site':item.work_mode==='remote'?'Remote':'Hybrid').toBe(selection);
  }
  await mode(page).getByLabel(selection,{exact:true}).uncheck();
 }
});
test('BRW-008 @regression Hours ranges filter under five, five to ten, over ten',async({page})=>{
 await browse(page);
 for(const [selection,expected] of [['Under 5 hours',2],['5–10 hours',3],['More than 10 hours',1]]){
   await hours(page).getByLabel(selection).check();await expect(visibleBrowseCards(page)).toHaveCount(expected);
   await hours(page).getByLabel(selection).uncheck();
 }
});
test('BRW-009 @regression Skills filter includes only selected skill',async({page})=>{
 await browse(page);await skills(page).getByLabel('Spreadsheets').check();
 await expect(visibleBrowseCards(page)).toHaveCount(2);
 for(const title of await titleList(page))expect(baseItems.find(x=>x.title===title).skills.some(x=>x.name==='Spreadsheets')).toBe(true);
});
test('BRW-010 @regression Multiple filters must intersect and update count',async({page})=>{
 await browse(page);
 await category(page).getByLabel('Knowledge-based').check();
 await mode(page).getByLabel('Remote',{exact:true}).check();
 await skills(page).getByLabel('Spreadsheets').check();
 await expect(visibleBrowseCards(page)).toHaveCount(1);
 await expect(visibleBrowseCards(page).first()).toContainText('Data Entry Support');
 await expect(browseCount(page)).toHaveText('1');
});
test('BRW-012 @regression Upcoming deadline sorts ascending',async({page})=>{
 await browse(page);await page.getByRole('combobox',{name:'Sort opportunities'}).selectOption('deadline');
 const observed=await titleList(page);
 const expected=[...baseItems].sort((a,b)=>a.application_deadline.localeCompare(b.application_deadline)).map(x=>x.title);
 expect(observed).toEqual(expected);
});
test('BRW-013 @regression Latest deadline sorts descending',async({page})=>{
 await browse(page);await page.getByRole('combobox',{name:'Sort opportunities'}).selectOption('latest');
 const observed=await titleList(page);
 const expected=[...baseItems].sort((a,b)=>b.application_deadline.localeCompare(a.application_deadline)).map(x=>x.title);
 expect(observed).toEqual(expected);
});
test('BRW-014 @regression Title A-Z sorts alphabetically',async({page})=>{
 await browse(page);await page.getByRole('combobox',{name:'Sort opportunities'}).selectOption('title');
 expect(await titleList(page)).toEqual(baseItems.map(x=>x.title).sort((a,b)=>a.localeCompare(b)));
});
test('BRW-017 @regression Hide/show filters preserves selection and results',async({page})=>{
 await browse(page);await category(page).getByLabel('Community').check();
 await expect(visibleBrowseCards(page)).toHaveCount(3);
 await page.getByRole('button',{name:'Hide filters'}).click();
 await expect(page.locator('.browse-filters')).toHaveCount(0);
 await expect(visibleBrowseCards(page)).toHaveCount(3);
 await page.getByRole('button',{name:'Show filters'}).click();
 await expect(category(page).getByLabel('Community')).toBeChecked();
 await expect(visibleBrowseCards(page)).toHaveCount(3);
});
test('BRW-018 @regression API error and Try again recovers on retry',async({page})=>{
 let requests=0;
 await mockApi(page,async(route,path)=>{
  if(path.endsWith('/opportunities')){
   requests++;
   return requests===1?jsonReply(route,503,{detail:'Temporary failure'}):jsonReply(route,200,{items:baseItems,total:baseItems.length});
  }
  return jsonReply(route,404,{});
 });
 await page.goto('/opportunities');
 await expect(page.getByRole('heading',{name:'Unable to load opportunities'})).toBeVisible();
 await page.getByRole('button',{name:'Try again'}).click();
 await expect(visibleBrowseCards(page)).toHaveCount(baseItems.length);
 expect(requests).toBeGreaterThanOrEqual(2);
});
