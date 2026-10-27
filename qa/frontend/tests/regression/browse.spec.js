import {test,expect} from '../../helpers/screenshot-every-test.js';
import {baseItems,openFixture,openHome,cards,names,search,sort,checkbox,cardFor,dialog,countLabel,dataItem,offsetDay} from '../../helpers/ui-fixtures.js';
// Built-in screenshot attachment for passed and failed tests.
test.use({ screenshot: 'on' });

const sorted=(titles)=>[...titles].sort((a,b)=>a.localeCompare(b));
const expectedItems=(...ids)=>baseItems.filter(o=>ids.includes(o.opportunity_id)).map(o=>o.title);
const assertTitles=async(page,titles)=>expect.poll(async()=>(await names(page)).sort()).toEqual([...titles].sort());
const browse=async(page)=>openFixture(page);
const category=(page,name)=>checkbox(page,'Category',name);
const mode=(page,name)=>checkbox(page,'Work mode',name);
const hours=(page,name)=>checkbox(page,'Time commitment',name);
const skills=(page,name)=>checkbox(page,'Skills',name);
const openDetail=async(page,title)=>{await cardFor(page,title).getByRole('button',{name:'View Details'}).click();await expect(dialog(page)).toBeVisible();};

// Search combinations and edge cases: BRW-008—017.
test('BRW-008 @regression search matches organization',async({page})=>{
  await browse(page);await search(page).fill('Maple Street Bakery');await assertTitles(page,expectedItems(101));
});
test('BRW-009 @regression search matches skill labels',async({page})=>{
  await browse(page);await search(page).fill('Spreadsheets');await assertTitles(page,expectedItems(101,103));
});
test('BRW-010 @regression search matches description',async({page})=>{
  await browse(page);await search(page).fill('Organize community spreadsheets');await assertTitles(page,expectedItems(101));
});
test('BRW-011 @regression search matches location',async({page})=>{
  await browse(page);await search(page).fill('Calgary');await assertTitles(page,expectedItems(101,102,103,105,106));
});
test('BRW-012 @regression search matches category and mode terms',async({page})=>{
  await browse(page);await search(page).fill('knowledge-based');await assertTitles(page,expectedItems(101,103,104));
  await search(page).fill('REMOTE');await assertTitles(page,expectedItems(101,104));
});
test('BRW-013 @regression search is case insensitive',async({page})=>{
  await browse(page);
  for(const query of ['GARDEN','garden','Garden']) {await search(page).fill(query);await assertTitles(page,expectedItems(102));}
});
test('BRW-014 @regression search trims surrounding whitespace',async({page})=>{
  await browse(page);await search(page).fill('  garden  ');await assertTitles(page,expectedItems(102));
});
test('BRW-015 @regression no-match search shows empty state and clear',async({page})=>{
  await browse(page);await search(page).fill('xyz-no-results');
  await expect(page.getByRole('heading',{name:'No opportunities found'})).toBeVisible();
  await expect(cards(page)).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Clear filters',exact:true})).toBeVisible();
});
test('BRW-016 @regression search X clears search and cards reset',async({page})=>{
  await browse(page);await search(page).fill('garden');
  await page.getByRole('button',{name:'Clear search'}).click();
  await expect(search(page)).toHaveValue('');await expect(cards(page)).toHaveCount(baseItems.length);
});
test('BRW-017 @regression empty and whitespace-only searches match all cards',async({page})=>{
  await browse(page);
  for(const query of ['', '   ']){await search(page).fill(query);await expect(cards(page)).toHaveCount(baseItems.length);}
});

// Filters. Parameterized controls keep clear, independent test IDs and screenshots.
test('BRW-018 @regression multiple category selections use OR',async({page})=>{
  await browse(page);await category(page,'Knowledge-based').check();await category(page,'Community').check();
  await expect(cards(page)).toHaveCount(baseItems.length);
});
test('BRW-019 @regression unchecking category restores unfiltered results',async({page})=>{
  await browse(page);await category(page,'Community').check();await expect(cards(page)).toHaveCount(3);
  await category(page,'Community').uncheck();await expect(cards(page)).toHaveCount(baseItems.length);
});
for(const [id,label,expected] of [
 ['BRW-020','Remote',expectedItems(101,104)],
 ['BRW-021','On-site',expectedItems(102,105)],
 ['BRW-022','Hybrid',expectedItems(103,106)]
]) test(`${id} @regression work mode ${label} selects matching cards`,async({page})=>{
  await browse(page);await mode(page,label).check();await assertTitles(page,expected);
});
test('BRW-023 @regression multiple work modes combine using OR',async({page})=>{
  await browse(page);await mode(page,'Remote').check();await mode(page,'Hybrid').check();await assertTitles(page,expectedItems(101,103,104,106));
});
for(const [id,label,expected] of [
 ['BRW-024','Under 5 hours',expectedItems(102,104)],
 ['BRW-025','5–10 hours',expectedItems(101,105,106)],
 ['BRW-026','More than 10 hours',expectedItems(103)]
]) test(`${id} @regression time range ${label} enforces boundaries`,async({page})=>{
  await browse(page);await hours(page,label).check();await assertTitles(page,expected);
});
test('BRW-027 @regression multiple hour ranges combine using OR',async({page})=>{
  await browse(page);await hours(page,'Under 5 hours').check();await hours(page,'More than 10 hours').check();
  await assertTitles(page,expectedItems(102,103,104));
});
test('BRW-028 @regression one skill checkbox restricts results',async({page})=>{
  await browse(page);await skills(page,'Spreadsheets').check();await assertTitles(page,expectedItems(101,103));
});
test('BRW-029 @regression multiple skills combine using OR',async({page})=>{
  await browse(page);await skills(page,'Spreadsheets').check();await skills(page,'Event setup').check();
  await assertTitles(page,expectedItems(101,102,103,106));
});
test('BRW-030 @regression unique skill appears dynamically as a checkbox',async({page})=>{
  const item=dataItem(150,'One-off Task',{skills:[{name:'CNC calibration'}]});
  await openFixture(page,{items:[item]});await expect(skills(page,'CNC calibration')).toBeVisible();
  await skills(page,'CNC calibration').check();await expect(cards(page)).toHaveCount(1);
});
test('BRW-031 @regression category and mode combine using AND',async({page})=>{
  await browse(page);await category(page,'Knowledge-based').check();await mode(page,'Remote').check();await assertTitles(page,expectedItems(101,104));
});
test('BRW-032 @regression search skill and hours combine using AND',async({page})=>{
  await browse(page);await search(page).fill('inventory');await skills(page,'Spreadsheets').check();
  await hours(page,'More than 10 hours').check();await assertTitles(page,expectedItems(103));
});
test('BRW-033 @regression conflicting filters result in empty state',async({page})=>{
  await browse(page);await category(page,'Community').check();await mode(page,'Remote').check();
  await expect(cards(page)).toHaveCount(0);
  await expect(page.getByRole('heading',{name:'No opportunities found'})).toBeVisible();
});
test('BRW-034 @regression showing results count updates with filters',async({page})=>{
  await browse(page);await expect(countLabel(page)).toHaveText('6');
  await mode(page,'Remote').check();await expect(countLabel(page)).toHaveText('2');
  await search(page).fill('Content');await expect(countLabel(page)).toHaveText('1');
});
test('BRW-035 @regression inline clear applied filters resets state',async({page})=>{
  await browse(page);await search(page).fill('garden');
  await page.getByRole('button',{name:'Clear applied filters'}).click();
  await expect(search(page)).toHaveValue('');await expect(cards(page)).toHaveCount(6);
});
test('BRW-036 @regression Clear all resets search filters and sorting',async({page})=>{
  await browse(page);await category(page,'Knowledge-based').check();await mode(page,'Remote').check();await search(page).fill('Data');
  await sort(page).selectOption('title');await page.getByRole('button',{name:'Clear all'}).click();
  await expect(category(page,'Knowledge-based')).not.toBeChecked();
  await expect(search(page)).toHaveValue('');await expect(sort(page)).toHaveValue('deadline');
  await expect(cards(page)).toHaveCount(6);
});
test('BRW-037 @regression Hide filters removes sidebar without hiding results',async({page})=>{
  await browse(page);await page.getByRole('button',{name:'Hide filters'}).click();
  await expect(page.locator('.browse-filters')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Show filters'})).toBeVisible();
  await expect(cards(page)).toHaveCount(6);
});
test('BRW-038 @regression Show filters preserves selected filters',async({page})=>{
  await browse(page);await category(page,'Community').check();
  await page.getByRole('button',{name:'Hide filters'}).click();
  await page.getByRole('button',{name:'Show filters'}).click();
  await expect(category(page,'Community')).toBeChecked();await expect(cards(page)).toHaveCount(3);
});
test('BRW-039 @regression inline Clear while sidebar hidden restores results',async({page})=>{
  await browse(page);await category(page,'Community').check();
  await page.getByRole('button',{name:'Hide filters'}).click();
  await page.getByRole('button',{name:'Clear applied filters'}).click();
  await expect(cards(page)).toHaveCount(6);
});

// Sorting.
test('BRW-040 @regression upcoming deadline is ascending by default',async({page})=>{
  await browse(page);await expect(sort(page)).toHaveValue('deadline');
  await expect.poll(()=>names(page)).toEqual(['Community Garden Cleanup','Data Entry Support','Inventory Spreadsheet Cleanup','On-site Photography','Remote Content Review','Hybrid Event Planning']);
});
test('BRW-041 @regression latest deadline sorts descending',async({page})=>{
  await browse(page);await sort(page).selectOption('latest');
  await expect.poll(()=>names(page)).toEqual(['Hybrid Event Planning','Remote Content Review','On-site Photography','Inventory Spreadsheet Cleanup','Data Entry Support','Community Garden Cleanup']);
});
test('BRW-042 @regression Title A–Z sorts alphabetically',async({page})=>{
  await browse(page);await sort(page).selectOption('title');
  await expect.poll(()=>names(page)).toEqual(sorted(baseItems.map(o=>o.title)));
});
test('BRW-043 @regression filtered subset remains alphabetically sorted',async({page})=>{
  await browse(page);await category(page,'Knowledge-based').check();await sort(page).selectOption('title');
  await expect.poll(()=>names(page)).toEqual(sorted(expectedItems(101,103,104)));
});

// Details dialog.
test('BRW-044 @regression detail dialog corresponds to clicked card',async({page})=>{
  await browse(page);await openDetail(page,'Data Entry Support');
  await expect(dialog(page).getByRole('heading',{name:'Data Entry Support'})).toBeVisible();
  await expect(dialog(page)).toContainText('Maple Street Bakery');
  await expect(dialog(page)).toContainText('Organize community spreadsheets.');
  await expect(dialog(page)).toContainText('Spreadsheets');
  await expect(dialog(page)).toContainText('Remote');
  await expect(dialog(page)).toContainText('8 hrs');
});
test('BRW-045 @regression X icon closes details dialog',async({page})=>{
  await browse(page);await openDetail(page,'Data Entry Support');
  await dialog(page).getByRole('button',{name:'Close details',exact:true}).click();
  await expect(dialog(page)).toHaveCount(0);
});
test('BRW-046 @regression clicking outside modal closes it',async({page})=>{
  await browse(page);await openDetail(page,'Data Entry Support');
  await page.locator('.browse-modal-backdrop').click({position:{x:5,y:5}});
  await expect(dialog(page)).toHaveCount(0);
});
test('BRW-047 @regression clicking inside dialog does not dismiss it',async({page})=>{
  await browse(page);await openDetail(page,'Data Entry Support');
  await dialog(page).locator('.browse-modal-description').click();
  await expect(dialog(page)).toBeVisible();
});
test('BRW-048 @regression missing description uses contact fallback',async({page})=>{
  await openFixture(page,{items:[dataItem(151,'No Description',{description:null})]});
  await openDetail(page,'No Description');
  await expect(dialog(page)).toContainText('Contact the organization for more information');
});
test('BRW-049 @regression empty skills array renders safe empty section',async({page})=>{
  await openFixture(page,{items:[dataItem(152,'No Skills',{skills:[]})]});
  await openDetail(page,'No Skills');
  await expect(dialog(page).getByRole('heading',{name:'Skills required'})).toBeVisible();
  await expect(dialog(page).locator('.browse-tags .browse-tag')).toHaveCount(0);
});
test('BRW-050 @regression keyboard Enter on close button dismisses dialog',async({page})=>{
  await browse(page);await openDetail(page,'Data Entry Support');
  const close=dialog(page).getByRole('button',{name:'Close Details',exact:true});
  await close.focus();await page.keyboard.press('Enter');await expect(dialog(page)).toHaveCount(0);
});

// Dates, loading and error states.
test('BRW-051 @regression future today past and missing deadline labels',async({page})=>{
  const items=[
    dataItem(201,'Future Due',{application_deadline:offsetDay(5)}),
    dataItem(202,'Due Today',{application_deadline:offsetDay(0)}),
    dataItem(203,'Overdue',{application_deadline:offsetDay(-4)}),
    dataItem(204,'No Deadline',{application_deadline:null}),
  ];
  await openFixture(page,{items});
  await expect(cardFor(page,'Future Due')).toContainText(/days left/);
  await expect(cardFor(page,'Due Today')).toContainText('Deadline today');
  await expect(cardFor(page,'Overdue')).toContainText('Deadline passed');
  await expect(cardFor(page,'No Deadline')).not.toContainText('days left');
});
test('BRW-052 @regression missing and malformed deadlines show Not specified',async({page})=>{
  await openFixture(page,{items:[dataItem(211,'Missing Deadline',{application_deadline:null}),dataItem(212,'Invalid Deadline',{application_deadline:'invalid'})]});
  for(const title of ['Missing Deadline','Invalid Deadline']){
    await expect(cardFor(page,title)).toContainText('Deadline: Not specified');
    await openDetail(page,title);await expect(dialog(page)).toContainText('Not specified');
    await dialog(page).getByRole('button',{name:'Close Details',exact:true}).click();
  }
});
test('BRW-053 @regression empty successful response shows zero count',async({page})=>{
  await openFixture(page,{items:[]});
  await expect(countLabel(page)).toHaveText('0');
  await expect(page.getByRole('heading',{name:'No opportunities found'})).toBeVisible();
});
test('BRW-054 @regression HTTP 500 shows useful error UI',async({page})=>{
  await openFixture(page,{status:500});
  await expect(page.getByRole('heading',{name:'Unable to load opportunities'})).toBeVisible();
  await expect(page.getByText(/HTTP 500/)).toBeVisible();
});
test('BRW-055 @regression Try again reloads after transient server failure',async({page})=>{
  let calls=0;
  await page.route('**/api/v1/opportunities?**',async route=>{
    calls+=1;
    await route.fulfill({status:calls===1?500:200,contentType:'application/json',body:JSON.stringify(calls===1?{error:'Server error'}:{items:baseItems,total:baseItems.length})});
  });
  await page.goto('/opportunities');
  await expect(page.getByRole('heading',{name:'Unable to load opportunities'})).toBeVisible();
  await page.getByRole('button',{name:'Try again'}).click();
  await expect(cards(page)).toHaveCount(6);
  expect(calls).toBeGreaterThanOrEqual(2);
});
test('BRW-056 @regression malformed payload triggers validation error',async({page})=>{
  await openFixture(page,{payload:{total:4}});
  await expect(page.getByRole('heading',{name:'Unable to load opportunities'})).toBeVisible();
  await expect(page.getByText(/expected an items array/)).toBeVisible();
});
test('BRW-057 @regression aborted network request shows error rather than crash',async({page})=>{
  await openFixture(page,{networkFailure:true});
  await expect(page.getByRole('heading',{name:'Unable to load opportunities'})).toBeVisible();
});
test('BRW-058 @regression optional API fields fall back without crashing',async({page})=>{
  const sparse={opportunity_id:220,title:null,description:null,category:null,organization:null,work_mode:null,expected_hours:null,application_deadline:null,skills:null,location:null};
  await openFixture(page,{items:[sparse]});
  const card=cardFor(page,'Untitled opportunity');
  await expect(card).toContainText('Organization');
  await expect(card).toContainText('Location not specified');
  await expect(card).toContainText('Flexible hours');
  await expect(card).toContainText('General');
});
test('BRW-059 @regression opportunity card renders mapped metadata and tags',async({page})=>{
  await browse(page);const card=cardFor(page,'Data Entry Support');
  for(const item of ['Maple Street Bakery','Organize community spreadsheets','Calgary','Remote','8 hrs','Knowledge-based','Spreadsheets']) await expect(card).toContainText(item);
  await expect(card).toContainText('Deadline:');
});

// Layout, accessibility and return navigation.
for(const [id,width,height] of [['BRW-060',390,844],['BRW-061',768,1024]]){
  test(`${id} @regression Browse toolbar and detail actions remain accessible at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height});await browse(page);
    await expect(search(page)).toBeVisible();await expect(sort(page)).toBeVisible();
    await expect(cardFor(page,'Data Entry Support').getByRole('button',{name:'View Details'})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+2)).toBe(true);
  });
}
test('BRW-062 @regression filter checkbox supports focus and Space key',async({page})=>{
  await browse(page);const input=category(page,'Community');
  await input.focus();await expect(input).toBeFocused();await page.keyboard.press('Space');
  await expect(input).toBeChecked();await expect(cards(page)).toHaveCount(3);
});
test('BRW-063 @regression search field is accessible using keyboard',async({page})=>{
  await browse(page);const input=search(page);await input.focus();
  await expect(input).toBeFocused();await page.keyboard.type('garden');
  await expect(cards(page)).toHaveCount(1);
});
test('BRW-064 @regression dialog exposes dialog role and accessible title',async({page})=>{
  await browse(page);await openDetail(page,'Data Entry Support');
  await expect(dialog(page)).toHaveAttribute('aria-modal','true');
  await expect(page.getByRole('dialog',{name:'Data Entry Support'})).toBeVisible();
});
test('BRW-065 @regression Browse Back to top scrolls to start',async({page})=>{
  await browse(page);await page.evaluate(()=>window.scrollTo(0,document.body.scrollHeight));
  const button=page.getByRole('button',{name:'Back to top'});
  await expect(button).toHaveClass(/visible/);
  await button.click();await expect.poll(()=>page.evaluate(()=>window.scrollY)).toBeLessThan(30);
});
test('BRW-066 @regression Browse Home link returns to landing',async({page})=>{
  await browse(page);await page.getByRole('link',{name:'Home',exact:true}).click();
  await expect(page).toHaveURL(/\/$/);await expect(page.getByRole('heading',{level:1})).toContainText('Earn Experience.');
});
